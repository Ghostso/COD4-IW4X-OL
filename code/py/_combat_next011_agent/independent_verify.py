#!/usr/bin/env python3
"""Independent NEXT-011 verifier (agent-authored, written from scratch).

Reads ONLY the frozen capture (capture-21-5.meta/.hex), the local crypto
module, and the local key files.  Writes derived, key-free artifacts under
_combat_next011_agent.  Re-derives every reported number from raw bytes
instead of trusting any earlier derived file.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "REF_LOBBY_KIT_CAP009"
OUT = Path(__file__).resolve().parent

EXPECT_META = "8242E2CEF7DFDEB8408838FE107738268E80C823FAF0473919C4D62A6DC4DFF5"
EXPECT_HEX = "3C939DDCA07ACCF3CC20D46BCFD31745E3C6420353A624ADAF5848EBAB94B653"


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def load_crypto():
    spec = importlib.util.spec_from_file_location("cc_local", CAP / "codol_crypto.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_keys():
    fields = {}
    for line in (CAP / "secrets.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"aes_out", "aes_in", "hmac_out", "hmac_in"}:
            fields[parts[0]] = bytes.fromhex(parts[1])
    return fields


def walk_tags(data):
    fields = []
    errors = []
    off = 0
    names = {0x01: "bool", 0x03: "u8", 0x06: "u16", 0x07: "i32",
             0x08: "u32", 0x09: "i64", 0x0A: "u64", 0x10: "string", 0x13: "blob"}
    while off < len(data):
        start = off
        tag = data[off]
        off += 1
        try:
            if tag == 0x13:
                if data[off] != 0x08:
                    raise ValueError("blob missing 0x08 length tag")
                off += 1
                size = struct.unpack_from("<I", data, off)[0]
                off += 4
                val = data[off:off + size]
                if len(val) != size:
                    raise ValueError("blob overruns object")
                off += size
                value = {"len": size, "hex": val.hex()}
            elif tag == 0x10:
                nul = data.find(b"\x00", off)
                if nul < 0:
                    raise ValueError("unterminated string")
                value = data[off:nul].decode("utf-8", "replace")
                off = nul + 1
            elif tag in (0x01, 0x03):
                value = data[off]; off += 1
            elif tag == 0x06:
                value = struct.unpack_from("<H", data, off)[0]; off += 2
            elif tag == 0x07:
                value = struct.unpack_from("<i", data, off)[0]; off += 4
            elif tag == 0x08:
                value = struct.unpack_from("<I", data, off)[0]; off += 4
            elif tag == 0x09:
                value = struct.unpack_from("<q", data, off)[0]; off += 8
            elif tag == 0x0A:
                value = struct.unpack_from("<Q", data, off)[0]; off += 8
            else:
                raise ValueError("unknown tag 0x%02x" % tag)
        except (ValueError, IndexError) as exc:
            errors.append("tag 0x%02x at +0x%04x: %s" % (tag, start, exc))
            break
        fields.append({"field": len(fields) + 1, "offset": start, "tag": tag,
                       "type": names.get(tag, "t%02x" % tag), "length": off - start,
                       "value": value})
    return fields, off, errors


def search_value(obj, value):
    hits = []
    patterns = []
    for w in (1, 2, 4, 8):
        if value <= (1 << (8 * w)) - 1:
            for end, enc in (("LE", "little"), ("BE", "big")):
                patterns.append(("u%d%s" % (w, end), value.to_bytes(w, enc, signed=False)))
        if -(1 << (8 * w - 1)) <= value <= (1 << (8 * w - 1)) - 1:
            for end, enc in (("LE", "little"), ("BE", "big")):
                patterns.append(("i%d%s" % (w, end), value.to_bytes(w, enc, signed=True)))
    patterns.append(("ascii-dec", str(value).encode()))
    seen = set()
    for label, pat in patterns:
        if (label, pat) in seen or not pat:
            continue
        seen.add((label, pat))
        offs, s = [], 0
        while True:
            k = obj.find(pat, s)
            if k < 0:
                break
            offs.append(k)
            s = k + 1
        if offs:
            hits.append({"encoding": label, "bytes": pat.hex(), "count": len(offs),
                         "offsets": ["0x%04x" % o for o in offs]})
    return hits


def parse_reply(body):
    off = 0
    res = {}
    if body[off] != 0x0A:
        return {"error": "no reply_id tag"}
    off += 1
    res["reply_id"] = struct.unpack_from("<Q", body, off)[0]; off += 8
    if body[off] != 0x08:
        return {"error": "no status tag"}
    off += 1
    res["status"] = struct.unpack_from("<I", body, off)[0]; off += 4
    if body[off] != 0x03:
        return {"error": "no task tag"}
    off += 1
    res["task"] = body[off]; off += 1
    if body[off] != 0x08:
        return {"error": "no object_count tag"}
    off += 1
    res["object_count"] = struct.unpack_from("<I", body, off)[0]; off += 4
    if body[off] != 0x08:
        return {"error": "no object_count_2 tag"}
    off += 1
    res["object_count_2"] = struct.unpack_from("<I", body, off)[0]; off += 4
    res["object_prefix_len"] = off
    res["object"] = body[off:]
    return res


def main():
    cc = load_crypto()
    keys = read_keys()
    mraw = (CAP / "capture-21-5.meta").read_bytes()
    hraw = (CAP / "capture-21-5.hex").read_bytes()
    meta_sha = sha256_hex(mraw)
    hex_sha = sha256_hex(hraw)

    report = {
        "meta_sha256": meta_sha,
        "hex_sha256": hex_sha,
        "meta_sha_match": meta_sha.upper() == EXPECT_META,
        "hex_sha_match": hex_sha.upper() == EXPECT_HEX,
    }

    session = {}
    meta_frames = []
    for ln, line in enumerate(mraw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        p = line.split()
        if p[1] == "SESSION-BEGIN":
            session = {"line": ln, "cid": p[2]}
            continue
        kv = {}
        for item in p[3:]:
            if "=" in item:
                k, v = item.split("=", 1)
                kv[k] = v
        meta_frames.append({"index": len(meta_frames) + 1, "cid": p[2], "dir": p[3], "kv": kv})

    hlines = hraw.decode("utf-8").splitlines()
    hex_frames = []
    i = 0
    while i < len(hlines):
        if not hlines[i].strip():
            i += 1
            continue
        hdr = hlines[i][1:].split()
        i += 1
        hx = hlines[i].strip()
        i += 1
        hex_frames.append({"index": len(hex_frames) + 1, "cid": hdr[0], "dir": hdr[1],
                           "declared_len": int(hdr[2].split("=")[1]), "raw": bytes.fromhex(hx)})

    report["session"] = session
    report["meta_frame_count"] = len(meta_frames)
    report["hex_frame_count"] = len(hex_frames)

    per_frame = []
    all_ok = True
    for mf, hf in zip(meta_frames, hex_frames):
        raw = hf["raw"]
        total = struct.unpack_from("<I", raw, 0)[0]
        checks = {
            "cid_match": mf["cid"] == hf["cid"],
            "dir_label_match": mf["dir"] == hf["dir"],
            "len_match": int(mf["kv"]["len"]) == hf["declared_len"] == len(raw),
            "sha_match": mf["kv"]["sha256"].lower() == sha256_hex(raw),
            "header_total_ok": total == len(raw) - 4,
            "magic_ab85": raw[4:6] == b"\xab\x85",
        }
        dec_out = cc.decrypt_task_frame(raw, keys["aes_out"], keys["hmac_out"])
        dec_in = cc.decrypt_task_frame(raw, keys["aes_in"], keys["hmac_in"])
        chosen = None
        if dec_out and dec_out["hmac_ok"] and dec_out["marker"] == 0x86:
            chosen = ("out", "C2S", dec_out)
        elif dec_in and dec_in["hmac_ok"] and dec_in["marker"] in (0x01, 0x02):
            chosen = ("in", "S2C", dec_in)
        ok = all(checks.values()) and chosen is not None
        all_ok = all_ok and ok
        per_frame.append({
            "index": mf["index"], "cid": mf["cid"], "meta_dir": mf["dir"],
            "seq": int(mf["kv"]["seq"]), "len": len(raw), "sha256": sha256_hex(raw),
            "checks": checks,
            "key_role": chosen[0] if chosen else None,
            "actual_dir": chosen[1] if chosen else None,
            "marker": chosen[2]["marker"] if chosen else None,
            "declared": chosen[2]["declared"] if chosen else None,
            "actual_service": chosen[2]["service"] if chosen and chosen[1] == "C2S" else None,
            "actual_task": chosen[2]["task"] if chosen and chosen[1] == "C2S" else None,
            "ok": ok,
        })
    report["all_frames_ok"] = all_ok
    report["frames"] = per_frame

    cycles = []
    for i in range(0, len(hex_frames) - 3, 4):
        hf_s2c = hex_frames[i + 1]
        hf_req = hex_frames[i + 2]
        d_s2c = cc.decrypt_task_frame(hf_s2c["raw"], keys["aes_in"], keys["hmac_in"])
        body = d_s2c["plain"][5:5 + d_s2c["declared"]]
        reply = parse_reply(body)
        obj = reply.get("object", b"")
        fields, consumed, errs = walk_tags(obj)
        d_req = cc.decrypt_task_frame(hf_req["raw"], keys["aes_out"], keys["hmac_out"])
        payload = d_req["payload"]
        m = re.search(rb"mmbook\s+([0-9]+)\s+([A-Za-z0-9+/=]+)\s+([0-9]+)", payload)
        A = int(m.group(1)) if m else None
        B = int(m.group(3)) if m else None
        tok = m.group(2).decode() if m else None
        tok_dec = base64.b64decode(tok).hex() if tok else None
        cycles.append({
            "cycle": len(cycles) + 1,
            "s2c_frame_index": per_frame[i + 1]["index"], "s2c_seq": per_frame[i + 1]["seq"],
            "s2c_len": len(hf_s2c["raw"]),
            "reply_id": reply.get("reply_id"), "status": reply.get("status"),
            "reply_task": reply.get("task"),
            "object_count": reply.get("object_count"), "object_count_2": reply.get("object_count_2"),
            "object_prefix_len": reply.get("object_prefix_len"),
            "object_len": len(obj), "object_sha256": sha256_hex(obj),
            "object_consumed": consumed, "walk_errors": errs, "field_count": len(fields),
            "object_hex": obj.hex(),
            "req614_frame_index": per_frame[i + 2]["index"], "req614_seq": per_frame[i + 2]["seq"],
            "req614_len": len(hf_req["raw"]),
            "payload_len": len(payload), "payload_hex": payload.hex(),
            "mmbook_A": A, "mmbook_B": B, "token_b64": tok, "token_decoded_hex": tok_dec,
            "A_hits": search_value(obj, A) if A is not None else [],
            "B_hits": search_value(obj, B) if B is not None else [],
        })

    report["cycles"] = cycles
    report["object_lengths"] = sorted({c["object_len"] for c in cycles})
    report["object_hashes"] = sorted({c["object_sha256"] for c in cycles})
    report["field_counts"] = sorted({c["field_count"] for c in cycles})
    report["mmbook_values"] = sorted({(c["mmbook_A"], c["mmbook_B"]) for c in cycles})
    report["cycle_object_lengths"] = [c["object_len"] for c in cycles]
    report["cycle_object_hashes"] = [c["object_sha256"] for c in cycles]

    accepted = {"occurrences": [], "markers": {}, "push_frames": []}
    for i, hf in enumerate(hex_frames):
        pf = per_frame[i]
        if pf["key_role"] is None:
            continue
        dec = cc.decrypt_task_frame(
            hf["raw"],
            keys["aes_in"] if pf["key_role"] == "in" else keys["aes_out"],
            keys["hmac_in"] if pf["key_role"] == "in" else keys["hmac_out"],
        )
        if not dec:
            continue
        mk = "0x%02x" % dec["marker"]
        accepted["markers"][mk] = accepted["markers"].get(mk, 0) + 1
        pt = dec["plain"]
        for needle in (b"accepted", b"mmbook accepted"):
            if needle in pt:
                accepted["occurrences"].append(
                    {"frame_index": pf["index"], "seq": pf["seq"],
                     "needle": needle.decode("latin1"), "plain_hex": pt.hex()})
        if dec["marker"] == 0x02:
            accepted["push_frames"].append({"frame_index": pf["index"], "seq": pf["seq"], "plain_hex": pt.hex()})
    report["accepted"] = accepted
    report["accepted_present"] = bool(accepted["occurrences"] or accepted["push_frames"])

    report["first_frame_hashes"] = {
        "21_5_request": per_frame[0]["sha256"], "21_5_response": per_frame[1]["sha256"],
        "6_14_request": per_frame[2]["sha256"], "6_14_response": per_frame[3]["sha256"]}

    (OUT / "independent_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("meta sha match :", report["meta_sha_match"], meta_sha)
    print("hex  sha match :", report["hex_sha_match"], hex_sha)
    print("frames         :", report["meta_frame_count"], report["hex_frame_count"])
    print("all frames ok  :", report["all_frames_ok"])
    print("object lengths :", report["object_lengths"])
    print("object hashes  :", report["object_hashes"])
    print("field counts   :", report["field_counts"])
    print("mmbook (A,B)   :", report["mmbook_values"])
    print("accepted       :", report["accepted_present"], accepted["markers"])
    c0 = cycles[0]
    print("cycle1 obj_len=%d prefix=%d consumed=%d walk_errors=%s" % (
        c0["object_len"], c0["object_prefix_len"], c0["object_consumed"], c0["walk_errors"]))
    print("cycle1 A=796 hits:", json.dumps(c0["A_hits"], ensure_ascii=False))
    print("cycle1 B=0 hit-encodings:", [h["encoding"] for h in c0["B_hits"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())