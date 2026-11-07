#!/usr/bin/env python3
"""Offline NEXT-011 decoder for the captured 21/5 and 6/14 frames.

The script only reads the frozen capture, crypto module, and local key files.
It writes derived, key-free JSON/TSV artifacts under _combat_next011.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import struct
from pathlib import Path
from typing import Any, Iterable


EXPECTED_META_SHA256 = "8242E2CEF7DFDEB8408838FE107738268E80C823FAF0473919C4D62A6DC4DFF5"
EXPECTED_HEX_SHA256 = "3C939DDCA07ACCF3CC20D46BCFD31745E3C6420353A624ADAF5848EBAB94B653"
EXPECTED_CID = "c0001"
EXPECTED_FRAME_COUNT = 44


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text_exact(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    return data, data.decode("utf-8")


def parse_meta(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data, text = read_text_exact(path)
    session: dict[str, Any] = {}
    frames: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.rstrip("\r\n").split()
        if len(parts) < 2:
            raise ValueError(f"{path}:{line_no}: malformed line")
        timestamp, kind = parts[0], parts[1]
        if kind == "SESSION-BEGIN":
            session = {
                "line_no": line_no,
                "timestamp": timestamp,
                "cid": parts[2],
                "fields": parts[3:],
            }
            continue
        if kind != "FRAME":
            raise ValueError(f"{path}:{line_no}: unexpected record kind {kind!r}")
        fields: dict[str, str] = {}
        for item in parts[3:]:
            if "=" in item:
                key, value = item.split("=", 1)
                fields[key] = value
        frames.append(
            {
                "line_no": line_no,
                "index": len(frames) + 1,
                "timestamp": timestamp,
                "cid": parts[2],
                "direction_label": parts[3],
                "fields": fields,
            }
        )
    return {
        "path": str(path),
        "length": len(data),
        "sha256": sha256_hex(data),
        "session": session,
        "frame_count": len(frames),
    }, frames


def parse_hex(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data, text = read_text_exact(path)
    lines = text.splitlines()
    frames: list[dict[str, Any]] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if not line:
            continue
        if not line.startswith(">"):
            raise ValueError(f"{path}:{idx}: expected '>' header, got {line!r}")
        header = line[1:].strip().split()
        if len(header) < 2:
            raise ValueError(f"{path}:{idx}: malformed hex header")
        cid = header[0]
        direction_label = header[1]
        length = None
        for item in header[2:]:
            if item.startswith("len="):
                length = int(item.split("=", 1)[1])
        if length is None:
            raise ValueError(f"{path}:{idx}: missing len= in header")
        hex_line_no = idx + 1
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines):
            raise ValueError(f"{path}:{idx}: missing hex payload")
        hex_text = lines[idx].strip()
        idx += 1
        try:
            raw = bytes.fromhex(hex_text)
        except ValueError as exc:
            raise ValueError(f"{path}:{hex_line_no}: invalid hex payload") from exc
        frames.append(
            {
                "index": len(frames) + 1,
                "header_line_no": hex_line_no - 1,
                "hex_line_no": hex_line_no,
                "cid": cid,
                "direction_label": direction_label,
                "declared_length": length,
                "raw": raw,
                "raw_len": len(raw),
                "sha256": sha256_hex(raw),
            }
        )
    return {
        "path": str(path),
        "length": len(data),
        "sha256": sha256_hex(data),
        "frame_count": len(frames),
    }, frames


def load_crypto_module(path: Path):
    spec = importlib.util.spec_from_file_location("combat_next011_codol_crypto", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_key_value_fields(path: Path) -> dict[str, bytes]:
    """Read only the hex-valued key fields used by the local capture keysets."""
    result: dict[str, bytes] = {}
    if not path.exists():
        return result
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split()
        if len(parts) != 2:
            continue
        key, value = parts
        if key not in {"aes_out", "aes_in", "hmac_out", "hmac_in"}:
            continue
        try:
            result[key] = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: invalid hex field") from exc
    return result


def load_keysets(capture_dir: Path) -> list[dict[str, Any]]:
    keysets: list[dict[str, Any]] = []
    sessions_path = capture_dir / "kdf_sessions.txt"
    if sessions_path.exists():
        for line_no, line in enumerate(sessions_path.read_text(encoding="utf-8").splitlines(), 1):
            parts = line.split()
            if len(parts) != 7:
                continue
            try:
                vals = [bytes.fromhex(part) for part in parts]
            except ValueError as exc:
                raise ValueError(f"{sessions_path}:{line_no}: invalid key hex") from exc
            keysets.append(
                {
                    "id": f"kdf-session-{len(keysets) + 1}",
                    "source_line": line_no,
                    "aes_out": vals[3],
                    "aes_in": vals[4],
                    "hmac_out": vals[5],
                    "hmac_in": vals[6],
                }
            )
    for filename in ("secrets_kdf.txt", "secrets.txt"):
        fields = parse_key_value_fields(capture_dir / filename)
        if fields.get("aes_out") and fields.get("aes_in") and fields.get("hmac_out") and fields.get("hmac_in"):
            keysets.append(
                {
                    "id": filename.removesuffix(".txt"),
                    "source_line": None,
                    "aes_out": fields["aes_out"],
                    "aes_in": fields["aes_in"],
                    "hmac_out": fields["hmac_out"],
                    "hmac_in": fields["hmac_in"],
                }
            )
    if not keysets:
        raise RuntimeError("no usable local keysets found")
    return keysets


def select_decryption(raw: bytes, keysets: list[dict[str, Any]], cc) -> tuple[dict[str, Any], Any, list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[bytes, bytes]] = set()
    for keyset in keysets:
        for role in ("out", "in"):
            aes_key = keyset[f"aes_{role}"]
            hmac_key = keyset[f"hmac_{role}"]
            pair = (aes_key, hmac_key)
            if pair in seen:
                continue
            seen.add(pair)
            dec = cc.decrypt_task_frame(raw, aes_key, hmac_key)
            if not dec or not dec.get("hmac_ok"):
                continue
            marker = dec["plain"][4] if len(dec["plain"]) >= 5 else None
            actual_direction = None
            if marker == 0x86:
                actual_direction = "C2S"
            elif marker in (0x01, 0x02):
                actual_direction = "S2C"
            candidates.append(
                {
                    "keyset_id": keyset["id"],
                    "key_role": role,
                    "actual_direction": actual_direction,
                    "dec": dec,
                }
            )
    if not candidates:
        raise RuntimeError("frame HMAC did not match any local keyset")
    expected_label = None
    if b"C2S" in raw[:0]:
        expected_label = "C2S"
    preferred = [c for c in candidates if c["actual_direction"] in ("C2S", "S2C")]
    selected = preferred[0] if preferred else candidates[0]
    public_candidates = [
        {
            "keyset_id": c["keyset_id"],
            "key_role": c["key_role"],
            "actual_direction": c["actual_direction"],
        }
        for c in candidates
    ]
    return selected, selected["dec"], public_candidates


def parse_u32(data: bytes, off: int) -> tuple[int, int]:
    if off + 4 > len(data):
        raise ValueError("truncated u32")
    return struct.unpack_from("<I", data, off)[0], off + 4


def parse_u64(data: bytes, off: int) -> tuple[int, int]:
    if off + 8 > len(data):
        raise ValueError("truncated u64")
    return struct.unpack_from("<Q", data, off)[0], off + 8


def parse_tagged_object(data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    fields: list[dict[str, Any]] = []
    errors: list[str] = []
    off = 0
    while off < len(data):
        start = off
        tag = data[off]
        off += 1
        value: Any = None
        payload_start = off
        payload_len = 0
        type_name = {
            0x01: "bool",
            0x03: "u8",
            0x06: "u16",
            0x07: "i32",
            0x08: "u32",
            0x09: "i64",
            0x0A: "u64",
            0x10: "string",
            0x13: "blob",
        }.get(tag, f"tag_{tag:02x}")
        try:
            if tag == 0x13:
                if off >= len(data) or data[off] != 0x08:
                    raise ValueError("blob missing u32 length tag")
                payload_start = off
                off += 1
                size, off = parse_u32(data, off)
                if off + size > len(data):
                    raise ValueError("blob length exceeds object")
                blob = data[off : off + size]
                value = {"length": size, "hex": blob.hex()}
                off += size
            elif tag == 0x10:
                nul = data.find(b"\x00", off)
                if nul < 0:
                    raise ValueError("unterminated string")
                raw = data[off:nul]
                value = raw.decode("utf-8", "replace")
                off = nul + 1
            elif tag == 0x01:
                if off >= len(data):
                    raise ValueError("truncated bool")
                value = data[off]
                off += 1
            elif tag == 0x03:
                if off >= len(data):
                    raise ValueError("truncated u8")
                value = data[off]
                off += 1
            elif tag == 0x06:
                if off + 2 > len(data):
                    raise ValueError("truncated u16")
                value = struct.unpack_from("<H", data, off)[0]
                off += 2
            elif tag == 0x07:
                if off + 4 > len(data):
                    raise ValueError("truncated i32")
                value = struct.unpack_from("<i", data, off)[0]
                off += 4
            elif tag == 0x08:
                value, off = parse_u32(data, off)
            elif tag == 0x09:
                if off + 8 > len(data):
                    raise ValueError("truncated i64")
                value = struct.unpack_from("<q", data, off)[0]
                off += 8
            elif tag == 0x0A:
                value, off = parse_u64(data, off)
            else:
                raise ValueError(f"unsupported tag 0x{tag:02x}")
        except ValueError as exc:
            errors.append(f"field {len(fields) + 1} at +0x{start:04x}: {exc}")
            break
        payload_end = off
        payload_len = payload_end - payload_start
        fields.append(
            {
                "field": len(fields) + 1,
                "offset": start,
                "offset_hex": f"0x{start:04x}",
                "tag": tag,
                "tag_hex": f"0x{tag:02x}",
                "type": type_name,
                "payload_offset": payload_start,
                "payload_length": payload_len,
                "field_length": off - start,
                "raw_hex": data[start:off].hex(),
                "value": value,
            }
        )
    if off != len(data):
        errors.append(f"object parser stopped at +0x{off:04x}, object length +0x{len(data):04x}")
    return fields, errors


def parse_reply_body(body: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"errors": [], "fields": []}
    off = 0
    try:
        if off >= len(body) or body[off] != 0x0A:
            raise ValueError("missing reply_id tag 0x0a")
        off += 1
        result["reply_id"], off = parse_u64(body, off)
        result["fields"].append({"name": "reply_id", "offset": 0, "length": off, "value": result["reply_id"]})
        start = off
        if off >= len(body) or body[off] != 0x08:
            raise ValueError("missing status tag 0x08")
        off += 1
        result["status"], off = parse_u32(body, off)
        result["fields"].append({"name": "status", "offset": start, "length": off - start, "value": result["status"]})
        start = off
        if off >= len(body) or body[off] != 0x03:
            raise ValueError("missing task tag 0x03")
        off += 1
        if off >= len(body):
            raise ValueError("truncated task")
        result["task"] = body[off]
        off += 1
        result["fields"].append({"name": "task", "offset": start, "length": off - start, "value": result["task"]})
        start = off
        if off >= len(body) or body[off] != 0x08:
            raise ValueError("missing object count tag 0x08")
        off += 1
        result["object_count"], off = parse_u32(body, off)
        result["fields"].append(
            {"name": "object_count", "offset": start, "length": off - start, "value": result["object_count"]}
        )
        result["object_prefix_length"] = off
        if result["object_count"]:
            start = off
            if off >= len(body) or body[off] != 0x08:
                raise ValueError("missing repeated object count tag 0x08")
            off += 1
            result["object_count_2"], off = parse_u32(body, off)
            result["fields"].append(
                {
                    "name": "object_count_2",
                    "offset": start,
                    "length": off - start,
                    "value": result["object_count_2"],
                }
            )
            result["object_prefix_length"] = off
        result["object_region_offset"] = off
        result["object_region_hex"] = body[off:].hex()
        result["object_region_length"] = len(body) - off
    except ValueError as exc:
        result["errors"].append(str(exc))
    return result


def find_occurrences(haystack: bytes, needle: bytes) -> list[int]:
    if not needle:
        return []
    offsets: list[int] = []
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx < 0:
            return offsets
        offsets.append(idx)
        start = idx + 1


def find_containing_fields(fields: list[dict[str, Any]], start: int, end: int) -> list[int]:
    return [
        field["field"]
        for field in fields
        if not (end <= field["offset"] or start >= field["offset"] + field["field_length"])
    ]


def candidate_patterns(value: int) -> Iterable[dict[str, Any]]:
    for width in (1, 2, 4, 8):
        max_unsigned = (1 << (8 * width)) - 1
        min_signed = -(1 << (8 * width - 1))
        max_signed = (1 << (8 * width - 1)) - 1
        if 0 <= value <= max_unsigned:
            for endian in ("little", "big"):
                encoding = "little" if endian == "little" else "big"
                raw = value.to_bytes(width, encoding, signed=False)
                yield {
                    "kind": "integer",
                    "representation": "unsigned",
                    "width": width,
                    "endian": endian,
                    "raw_hex": raw.hex(),
                    "bytes": raw,
                }
        if min_signed <= value <= max_signed:
            for endian in ("little", "big"):
                encoding = "little" if endian == "little" else "big"
                raw = value.to_bytes(width, encoding, signed=True)
                yield {
                    "kind": "integer",
                    "representation": "signed",
                    "width": width,
                    "endian": endian,
                    "raw_hex": raw.hex(),
                    "bytes": raw,
                }
    for label, raw in (
        ("ascii_decimal", str(value).encode("ascii")),
        ("ascii_hex_lower", format(value, "x").encode("ascii")),
        ("ascii_hex_upper", format(value, "X").encode("ascii")),
        ("ascii_0x_hex_lower", format(value, "#x").encode("ascii")),
        ("ascii_0x_hex_upper", format(value, "#X").encode("ascii")),
    ):
        yield {
            "kind": "ascii",
            "representation": label,
            "width": len(raw),
            "endian": None,
            "raw_hex": raw.hex(),
            "bytes": raw,
        }


def candidate_records(object_bytes: bytes, fields: list[dict[str, Any]], value: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for pattern in candidate_patterns(value):
        key = (
            pattern["kind"],
            pattern["representation"],
            pattern["width"],
            pattern["endian"],
            pattern["raw_hex"],
            value,
        )
        if key in seen:
            continue
        seen.add(key)
        offsets = find_occurrences(object_bytes, pattern["bytes"])
        if not offsets:
            continue
        detail = []
        for off in offsets:
            detail.append(
                {
                    "offset": off,
                    "offset_hex": f"0x{off:04x}",
                    "fields": find_containing_fields(fields, off, off + len(pattern["bytes"])),
                }
            )
        out.append(
            {
                "value": value,
                "kind": pattern["kind"],
                "representation": pattern["representation"],
                "width": pattern["width"],
                "endian": pattern["endian"],
                "raw_hex": pattern["raw_hex"],
                "match_count": len(offsets),
                "matches": detail,
            }
        )
    return out


def compress_offsets(offsets: list[int]) -> str:
    if not offsets:
        return ""
    runs: list[tuple[int, int]] = []
    start = prev = offsets[0]
    for off in offsets[1:]:
        if off == prev + 1:
            prev = off
            continue
        runs.append((start, prev))
        start = prev = off
    runs.append((start, prev))
    return ", ".join(
        f"0x{start:04x}" if start == end else f"0x{start:04x}-0x{end:04x}" for start, end in runs
    )


def parse_mmbook(payload: bytes) -> dict[str, Any]:
    match = re.search(rb"mmbook\s+([0-9]+)\s+([A-Za-z0-9+/=]+)\s+([0-9]+)", payload)
    if not match:
        return {"found": False}
    token = match.group(2)
    try:
        decoded = base64.b64decode(token, validate=True)
    except Exception:
        decoded = b""
    command_start = match.start()
    return {
        "found": True,
        "command_start": command_start,
        "command_end": match.end(),
        "command_text": match.group(0).decode("ascii", "replace"),
        "A": int(match.group(1)),
        "token_b64": token.decode("ascii"),
        "token_decoded_hex": decoded.hex(),
        "token_decoded_length": len(decoded),
        "B": int(match.group(3)),
    }


def build_frame_record(
    meta_frame: dict[str, Any],
    hex_frame: dict[str, Any],
    keysets: list[dict[str, Any]],
    cc,
) -> dict[str, Any]:
    raw = hex_frame["raw"]
    errors: list[str] = []
    meta_len = int(meta_frame["fields"].get("len", "-1"))
    meta_sha = meta_frame["fields"].get("sha256", "").lower()
    if meta_frame["cid"] != hex_frame["cid"]:
        errors.append("meta/hex cid mismatch")
    if meta_frame["direction_label"] != hex_frame["direction_label"]:
        errors.append("meta/hex direction label mismatch")
    if meta_len != hex_frame["declared_length"] or meta_len != len(raw):
        errors.append("meta/hex/raw length mismatch")
    if meta_sha != hex_frame["sha256"]:
        errors.append("meta/hex sha256 mismatch")
    if len(raw) < 34:
        errors.append("frame too short")
    total = struct.unpack_from("<I", raw, 0)[0]
    header_self_consistent = total == len(raw) - 4
    if not header_self_consistent:
        errors.append("u32 total_len is not raw_len - 4")
    if raw[4:6] != b"\xab\x85":
        errors.append("frame header is not AB 85")
    seq = struct.unpack_from("<I", raw, 6)[0]
    selected, dec, candidates = select_decryption(raw, keysets, cc)
    plain = dec["plain"]
    declared = dec["declared"]
    marker = plain[4]
    actual_direction = selected["actual_direction"]
    body = plain[5 : 5 + declared]
    if len(body) != declared:
        errors.append("declared plaintext body exceeds decrypted plaintext")

    actual_service = None
    actual_task = None
    actual_ver = None
    payload = b""
    reply = None
    if actual_direction == "C2S":
        actual_service = plain[5] if len(plain) >= 6 else None
        actual_ver = plain[6] if len(plain) >= 7 else None
        actual_task = plain[7] if len(plain) >= 8 else None
        payload = plain[8 : 8 + max(0, declared - 3)]
    elif actual_direction == "S2C" and marker == 0x01:
        reply = parse_reply_body(body)
        actual_task = reply.get("task")
    elif actual_direction == "S2C" and marker == 0x02:
        # The accepted check records push bodies verbatim; service/task are not
        # self-contained in a generic push envelope.
        payload = body

    meta_service = int(meta_frame["fields"].get("service", "-1"))
    meta_task = int(meta_frame["fields"].get("task", "-1"))
    if actual_direction == "C2S":
        if actual_service != meta_service or actual_task != meta_task:
            errors.append("decrypted C2S service/task differs from meta label")
    meta_seq = int(meta_frame["fields"].get("seq", "-1"))
    if meta_seq != seq:
        errors.append("decrypted seq differs from meta seq")

    return {
        "index": meta_frame["index"],
        "timestamp": meta_frame["timestamp"],
        "cid": meta_frame["cid"],
        "meta_direction_label": meta_frame["direction_label"],
        "hex_direction_label": hex_frame["direction_label"],
        "actual_direction": actual_direction,
        "message_marker": marker,
        "message_kind": {0x86: "client_task", 0x01: "server_reply", 0x02: "server_push"}.get(
            marker, f"unknown_{marker:02x}"
        ),
        "meta_service": meta_service,
        "meta_task": meta_task,
        "actual_service": actual_service,
        "actual_task": actual_task,
        "actual_version": actual_ver,
        "service_evidence": "plaintext field" if actual_direction == "C2S" else "associated request (S2C body has no service field)",
        "seq": seq,
        "meta_seq": meta_seq,
        "meta_length": meta_len,
        "hex_declared_length": hex_frame["declared_length"],
        "raw_length": len(raw),
        "raw_sha256": hex_frame["sha256"],
        "meta_sha256": meta_sha,
        "hash_verified": hex_frame["sha256"] == meta_sha,
        "header_total": total,
        "header_self_consistent": header_self_consistent,
        "header_magic": raw[4:6].hex(),
        "decryption_keyset": selected["keyset_id"],
        "decryption_key_role": selected["key_role"],
        "decryption_key_candidates": candidates,
        "hmac_ok": dec["hmac_ok"],
        "declared_body_length": declared,
        "decrypted_plain_length": len(plain),
        "plain_sha256": sha256_hex(plain),
        "plain_hex": plain.hex(),
        "body_hex": body.hex(),
        "payload_hex": payload.hex(),
        "payload_length": len(payload),
        "reply": reply,
        "errors": errors,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_tsv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    lines = ["\t".join(columns)]
    for row in rows:
        vals = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            vals.append(str(value).replace("\t", " ").replace("\r", " ").replace("\n", " "))
        lines.append("\t".join(vals))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    capture_dir = root / "REF_LOBBY_KIT_CAP009"
    meta_path = capture_dir / "capture-21-5.meta"
    hex_path = capture_dir / "capture-21-5.hex"
    crypto_path = capture_dir / "codol_crypto.py"

    meta_info, meta_frames = parse_meta(meta_path)
    hex_info, hex_frames = parse_hex(hex_path)
    if meta_info["sha256"].upper() != EXPECTED_META_SHA256:
        raise SystemExit(f"meta sha256 mismatch: {meta_info['sha256']}")
    if hex_info["sha256"].upper() != EXPECTED_HEX_SHA256:
        raise SystemExit(f"hex sha256 mismatch: {hex_info['sha256']}")
    if meta_info["frame_count"] != EXPECTED_FRAME_COUNT or hex_info["frame_count"] != EXPECTED_FRAME_COUNT:
        raise SystemExit(
            f"frame count mismatch: meta={meta_info['frame_count']} hex={hex_info['frame_count']}"
        )
    if len(meta_frames) != len(hex_frames):
        raise SystemExit("meta/hex frame count mismatch")

    cc = load_crypto_module(crypto_path)
    keysets = load_keysets(capture_dir)
    frames = [
        build_frame_record(meta_frame, hex_frame, keysets, cc)
        for meta_frame, hex_frame in zip(meta_frames, hex_frames)
    ]
    if any(frame["errors"] for frame in frames):
        failures = [{"index": f["index"], "errors": f["errors"]} for f in frames if f["errors"]]
        write_json(out / "fatal_errors.json", failures)
        raise SystemExit("frame validation failed; see fatal_errors.json")

    frame_index = {frame["index"]: frame for frame in frames}
    request_by_seq: dict[tuple[str, int], dict[str, Any]] = {}
    for frame in frames:
        if frame["actual_direction"] == "C2S":
            request_by_seq[(frame["cid"], frame["seq"])] = frame
    for frame in frames:
        if frame["actual_direction"] == "S2C":
            req = request_by_seq.get((frame["cid"], frame["seq"]))
            if req is None:
                frame["errors"].append("no same-cid/seq request for service association")
                frame["associated_request_service"] = None
                frame["associated_request_task"] = None
            else:
                frame["associated_request_service"] = req["actual_service"]
                frame["associated_request_task"] = req["actual_task"]
                if frame["actual_task"] != req["actual_task"]:
                    frame["errors"].append("S2C reply task differs from associated request task")

    objects: list[dict[str, Any]] = []
    for frame in frames:
        reply = frame.get("reply")
        if not reply or reply.get("errors"):
            continue
        if reply.get("object_count") != 1:
            continue
        raw_obj = bytes.fromhex(reply.get("object_region_hex", ""))
        fields, parse_errors = parse_tagged_object(raw_obj)
        object_record = {
            "frame_index": frame["index"],
            "cid": frame["cid"],
            "request_seq": frame["seq"],
            "associated_service": frame.get("associated_request_service"),
            "task": reply.get("task"),
            "reply_id": reply.get("reply_id"),
            "status": reply.get("status"),
            "object_count": reply.get("object_count"),
            "object_count_2": reply.get("object_count_2"),
            "object_prefix_length": reply.get("object_prefix_length"),
            "object_length": len(raw_obj),
            "object_sha256": sha256_hex(raw_obj),
            "object_hex": raw_obj.hex(),
            "parsed_field_count": len(fields),
            "parsed_consumed": sum(field["field_length"] for field in fields),
            "parse_errors": parse_errors,
            "fields": fields,
        }
        objects.append(object_record)

    mmbooks: list[dict[str, Any]] = []
    for frame in frames:
        if frame["actual_direction"] != "C2S":
            continue
        if frame["actual_service"] != 6 or frame["actual_task"] != 14:
            continue
        payload = bytes.fromhex(frame["payload_hex"])
        parsed = parse_mmbook(payload)
        mmbooks.append(
            {
                "frame_index": frame["index"],
                "cid": frame["cid"],
                "seq": frame["seq"],
                "payload_length": len(payload),
                "payload_sha256": sha256_hex(payload),
                "payload_hex": payload.hex(),
                **parsed,
            }
        )

    cycles: list[dict[str, Any]] = []
    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    for frame in frames:
        if frame["actual_direction"] == "C2S" and frame["actual_service"] == 21 and frame["actual_task"] == 5:
            key = (frame["cid"], frame["seq"])
            grouped.setdefault(key, {})["find_request"] = frame
        elif frame["actual_direction"] == "S2C" and frame.get("actual_task") == 5:
            key = (frame["cid"], frame["seq"])
            grouped.setdefault(key, {})["find_response"] = frame
        elif frame["actual_direction"] == "C2S" and frame["actual_service"] == 6 and frame["actual_task"] == 14:
            key = (frame["cid"], frame["seq"] - 1)
            grouped.setdefault(key, {})["mmbook_request"] = frame
        elif frame["actual_direction"] == "S2C" and frame.get("actual_task") == 14:
            key = (frame["cid"], frame["seq"] - 1)
            grouped.setdefault(key, {})["mmbook_response"] = frame

    object_by_frame = {obj["frame_index"]: obj for obj in objects}
    ab_candidates: list[dict[str, Any]] = []
    for cycle_no, key in enumerate(sorted(grouped, key=lambda item: grouped[item]["find_request"]["seq"]), 1):
        group = grouped[key]
        find_req = group.get("find_request")
        find_rep = group.get("find_response")
        mmbook_frame = group.get("mmbook_request")
        mmbook_rep = group.get("mmbook_response")
        obj = object_by_frame.get(find_rep["index"]) if find_rep else None
        mmbook_payload = bytes.fromhex(mmbook_frame["payload_hex"]) if mmbook_frame else b""
        mmbook = parse_mmbook(mmbook_payload) if mmbook_frame else {"found": False}
        candidates: dict[str, Any] = {"A": [], "B": []}
        if obj and mmbook.get("found"):
            obj_bytes = bytes.fromhex(obj["object_hex"])
            candidates["A"] = candidate_records(obj_bytes, obj["fields"], mmbook["A"])
            candidates["B"] = candidate_records(obj_bytes, obj["fields"], mmbook["B"])
        cycle = {
            "cycle": cycle_no,
            "cid": key[0],
            "request_seq": key[1],
            "find_request_frame": find_req["index"] if find_req else None,
            "find_response_frame": find_rep["index"] if find_rep else None,
            "mmbook_request_frame": mmbook_frame["index"] if mmbook_frame else None,
            "mmbook_response_frame": mmbook_rep["index"] if mmbook_rep else None,
            "find_request_payload_hex": find_req["payload_hex"] if find_req else "",
            "find_object_length": obj["object_length"] if obj else None,
            "find_object_sha256": obj["object_sha256"] if obj else None,
            "find_object_hex": obj["object_hex"] if obj else "",
            "mmbook": mmbook,
            "candidates": candidates,
        }
        cycles.append(cycle)
        for ab in ("A", "B"):
            for candidate in candidates[ab]:
                ab_candidates.append(
                    {
                        "cycle": cycle_no,
                        "request_seq": key[1],
                        "value_name": ab,
                        "value": candidate["value"],
                        "kind": candidate["kind"],
                        "representation": candidate["representation"],
                        "width": candidate["width"],
                        "endian": candidate["endian"],
                        "raw_hex": candidate["raw_hex"],
                        "match_count": candidate["match_count"],
                        "offsets": [m["offset_hex"] for m in candidate["matches"]],
                        "offset_ranges": compress_offsets([m["offset"] for m in candidate["matches"]]),
                        "fields": sorted(
                            {
                                field
                                for match in candidate["matches"]
                                for field in match["fields"]
                            }
                        ),
                    }
                )

    accepted_hits: list[dict[str, Any]] = []
    for frame in frames:
        if frame["actual_direction"] != "S2C":
            continue
        plain = bytes.fromhex(frame["plain_hex"])
        if b"mmbook accepted" in plain:
            accepted_hits.append(
                {
                    "frame_index": frame["index"],
                    "seq": frame["seq"],
                    "marker": frame["message_marker"],
                    "associated_service": frame.get("associated_request_service"),
                    "associated_task": frame.get("associated_request_task"),
                    "plain_hex": frame["plain_hex"],
                }
            )
    push_frames = [frame for frame in frames if frame["actual_direction"] == "S2C" and frame["message_marker"] == 0x02]
    mybook_s2c = [
        frame
        for frame in frames
        if frame["actual_direction"] == "S2C" and frame.get("associated_request_task") == 14
    ]
    accepted = {
        "meta_push_records": 0,
        "decrypted_push_frames": len(push_frames),
        "decrypted_push_indices": [frame["index"] for frame in push_frames],
        "mmbook_s2c_frames": len(mybook_s2c),
        "mmbook_s2c_markers": [frame["message_marker"] for frame in mybook_s2c],
        "mmbook_s2c_bodies_hex": [frame["body_hex"] for frame in mybook_s2c],
        "accepted_string_hits": accepted_hits,
        "accepted_present": bool(push_frames or accepted_hits),
        "conclusion": (
            "accepted push present in captured bytes"
            if (push_frames or accepted_hits)
            else "no accepted push and no accepted string in captured S2C bytes"
        ),
    }

    request_services: dict[tuple[int, int], int] = {}
    for frame in frames:
        if frame["actual_direction"] == "C2S":
            request_services[(frame["actual_service"], frame["actual_task"])] = (
                request_services.get((frame["actual_service"], frame["actual_task"]), 0) + 1
            )

    object_lengths = sorted({obj["object_length"] for obj in objects})
    object_hashes = sorted({obj["object_sha256"] for obj in objects})
    object_field_counts = sorted({obj["parsed_field_count"] for obj in objects})
    ab_values = sorted({(cycle["mmbook"].get("A"), cycle["mmbook"].get("B")) for cycle in cycles})

    summary = {
        "input_meta": {k: v for k, v in meta_info.items() if k != "session"},
        "input_hex": hex_info,
        "session": meta_info["session"],
        "frame_count": len(frames),
        "all_frames_cid_c0001": all(frame["cid"] == EXPECTED_CID for frame in frames),
        "all_hashes_verified": all(frame["hash_verified"] for frame in frames),
        "all_header_self_consistent": all(frame["header_self_consistent"] for frame in frames),
        "all_hmac_ok": all(frame["hmac_ok"] for frame in frames),
        "actual_direction_counts": {
            direction: sum(1 for frame in frames if frame["actual_direction"] == direction)
            for direction in ("C2S", "S2C")
        },
        "actual_service_task_counts": [
            {"service": key[0], "task": key[1], "count": count}
            for key, count in sorted(request_services.items(), key=lambda item: (item[0][0], item[0][1]))
        ],
        "sequence_list": [frame["seq"] for frame in frames],
        "response_object_lengths": object_lengths,
        "response_object_hashes": object_hashes,
        "response_object_field_counts": object_field_counts,
        "cycle_count": len(cycles),
        "mmbook_count": len(mmbooks),
        "mmbook_values": [{"A": item[0], "B": item[1]} for item in ab_values],
        "cycle_object_lengths": [cycle["find_object_length"] for cycle in cycles],
        "cycle_object_hashes": [cycle["find_object_sha256"] for cycle in cycles],
        "accepted": accepted,
        "first_frame_hashes": {
            "21_5_request": frames[0]["raw_sha256"],
            "21_5_response": frames[1]["raw_sha256"],
            "6_14_request": frames[2]["raw_sha256"],
            "6_14_response": frames[3]["raw_sha256"],
        },
    }

    inventory_rows = []
    for frame in frames:
        inventory_rows.append(
            {
                "index": frame["index"],
                "timestamp": frame["timestamp"],
                "cid": frame["cid"],
                "meta_direction": frame["meta_direction_label"],
                "actual_direction": frame["actual_direction"],
                "marker": f"0x{frame['message_marker']:02x}",
                "meta_service_task": f"{frame['meta_service']}/{frame['meta_task']}",
                "actual_service_task": (
                    f"{frame['actual_service']}/{frame['actual_task']}"
                    if frame["actual_direction"] == "C2S"
                    else f"{frame.get('associated_request_service')}/{frame['actual_task']}"
                ),
                "seq": frame["seq"],
                "raw_len": frame["raw_length"],
                "raw_sha256": frame["raw_sha256"],
                "header_total": frame["header_total"],
                "declared_body_length": frame["declared_body_length"],
                "plain_len": frame["decrypted_plain_length"],
                "plain_sha256": frame["plain_sha256"],
                "keyset": frame["decryption_keyset"],
                "hmac_ok": frame["hmac_ok"],
            }
        )
    object_rows = []
    for obj in objects:
        object_rows.append(
            {
                "frame_index": obj["frame_index"],
                "seq": obj["request_seq"],
                "service_task": f"{obj['associated_service']}/{obj['task']}",
                "reply_id": obj["reply_id"],
                "status": obj["status"],
                "object_count": obj["object_count"],
                "object_prefix_length": obj["object_prefix_length"],
                "object_length": obj["object_length"],
                "object_sha256": obj["object_sha256"],
                "parsed_field_count": obj["parsed_field_count"],
                "parse_errors": obj["parse_errors"],
            }
        )
    field_rows = []
    for obj in objects:
        for field in obj["fields"]:
            value = field["value"]
            if isinstance(value, dict):
                value = value.get("hex")
            field_rows.append(
                {
                    "frame_index": obj["frame_index"],
                    "seq": obj["request_seq"],
                    "object_length": obj["object_length"],
                    "field": field["field"],
                    "offset": field["offset_hex"],
                    "tag": field["tag_hex"],
                    "type": field["type"],
                    "payload_length": field["payload_length"],
                    "field_length": field["field_length"],
                    "value": value,
                    "raw_hex": field["raw_hex"],
                }
            )
    mmbook_rows = []
    for item in mmbooks:
        mmbook_rows.append(
            {
                "frame_index": item["frame_index"],
                "seq": item["seq"],
                "payload_length": item["payload_length"],
                "A": item.get("A"),
                "B": item.get("B"),
                "command_text": item.get("command_text"),
                "token_b64": item.get("token_b64"),
                "token_decoded_hex": item.get("token_decoded_hex"),
                "payload_sha256": item["payload_sha256"],
                "payload_hex": item["payload_hex"],
            }
        )

    write_json(out / "frame_inventory.json", frames)
    write_json(out / "plaintext_manifest.json", frames)
    write_json(out / "objects.json", objects)
    write_json(out / "cycles_ab_candidates.json", cycles)
    write_json(out / "ab_candidates.json", ab_candidates)
    write_json(out / "accepted_check.json", accepted)
    write_json(out / "summary.json", summary)
    write_tsv(
        out / "frame_inventory.tsv",
        inventory_rows,
        [
            "index",
            "timestamp",
            "cid",
            "meta_direction",
            "actual_direction",
            "marker",
            "meta_service_task",
            "actual_service_task",
            "seq",
            "raw_len",
            "raw_sha256",
            "header_total",
            "declared_body_length",
            "plain_len",
            "plain_sha256",
            "keyset",
            "hmac_ok",
        ],
    )
    write_tsv(
        out / "objects.tsv",
        object_rows,
        [
            "frame_index",
            "seq",
            "service_task",
            "reply_id",
            "status",
            "object_count",
            "object_prefix_length",
            "object_length",
            "object_sha256",
            "parsed_field_count",
            "parse_errors",
        ],
    )
    write_tsv(
        out / "object_fields.tsv",
        field_rows,
        [
            "frame_index",
            "seq",
            "object_length",
            "field",
            "offset",
            "tag",
            "type",
            "payload_length",
            "field_length",
            "value",
            "raw_hex",
        ],
    )
    write_tsv(
        out / "mmbook.tsv",
        mmbook_rows,
        [
            "frame_index",
            "seq",
            "payload_length",
            "A",
            "B",
            "command_text",
            "token_b64",
            "token_decoded_hex",
            "payload_sha256",
            "payload_hex",
        ],
    )
    write_tsv(
        out / "ab_candidates.tsv",
        ab_candidates,
        [
            "cycle",
            "request_seq",
            "value_name",
            "value",
            "kind",
            "representation",
            "width",
            "endian",
            "raw_hex",
            "match_count",
            "offsets",
            "offset_ranges",
            "fields",
        ],
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
