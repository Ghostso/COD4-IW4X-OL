# -*- coding: utf-8 -*-
"""Offline unpack of the CODOL 3.19 shell: AP32 sections and the AP32 carrier
inside the last .tp3 section.

No client is started and the source file is never modified.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

import aplib
import pefile

ROOT = Path(__file__).resolve().parent
SRC = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe")
WORK = ROOT / "work"


def log(msg: str) -> None:
    print(msg, flush=True)
    with (ROOT / "logs" / "unpack.log").open("a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_ap32_blocks(data: bytes) -> list[dict]:
    """Enumerate plausible AP32 blocks: 4-byte prefix + 'AP32' + 24-byte header."""
    blocks = []
    pos = 0
    while True:
        i = data.find(b"AP32", pos)
        if i < 0:
            break
        pos = i + 1
        if i < 4:
            continue
        try:
            hsize, packed, pcrc, orig, ocrc = struct.unpack_from("<IIIII", data, i + 4)
        except struct.error:
            break
        if hsize != 0x18 or not (0 < packed < 0x4000000) or not (0 < orig < 0x8000000):
            continue
        start = i + hsize
        stream = data[start:start + packed]
        if len(stream) != packed:
            continue
        ok_packed = (zlib.crc32(stream) & 0xFFFFFFFF) == pcrc
        entry = {
            "signature_off": i,
            "prefix": struct.unpack_from("<I", data, i - 4)[0],
            "packed_len": packed,
            "orig_len": orig,
            "packed_crc_ok": ok_packed,
        }
        try:
            out = bytes(aplib.APLib(stream).depack())
        except Exception as exc:  # noqa: BLE001
            entry["error"] = repr(exc)
            blocks.append(entry)
            continue
        entry["out_len"] = len(out)
        entry["out_crc_ok"] = (zlib.crc32(out) & 0xFFFFFFFF) == ocrc
        entry["out_sha256"] = sha256(out)
        entry["data"] = out
        blocks.append(entry)
    return blocks


def main() -> int:
    if not SRC.is_file():
        log(f"missing source: {SRC}")
        return 2
    (ROOT / "logs" / "unpack.log").write_text("", encoding="utf-8")
    raw = SRC.read_bytes()
    log(f"source={SRC}")
    log(f"source_size={len(raw)} sha256={sha256(raw)}")

    pe = pefile.PE(str(SRC), fast_load=True)
    sections = []
    for s in pe.sections:
        sections.append({
            "name": s.Name.rstrip(b"\0").decode("latin-1"),
            "va": s.VirtualAddress,
            "vsize": s.Misc_VirtualSize,
            "raw_ptr": s.PointerToRawData,
            "raw_size": s.SizeOfRawData,
            "chars": s.Characteristics,
        })
    log("sections: " + json.dumps(sections))
    log(f"TimeDateStamp=0x{pe.FILE_HEADER.TimeDateStamp:08X} "
        f"SizeOfImage=0x{pe.OPTIONAL_HEADER.SizeOfImage:X} "
        f"EntryRVA=0x{pe.OPTIONAL_HEADER.AddressOfEntryPoint:X}")

    blocks = find_ap32_blocks(raw)
    log(f"ap32_candidates={len(blocks)}")
    manifest = []
    for idx, b in enumerate(blocks):
        row = {k: v for k, v in b.items() if k != "data"}
        manifest.append(row)
        log(f"[{idx}] sig_off=0x{b['signature_off']:X} prefix=0x{b['prefix']:08X} "
            f"packed={b['packed_len']} orig={b['orig_len']} "
            f"packed_crc_ok={b['packed_crc_ok']} out_len={b.get('out_len')} "
            f"out_crc_ok={b.get('out_crc_ok')} err={b.get('error')}")
        if "data" in b and b.get("out_crc_ok"):
            (WORK / f"ap32_{idx:02d}_off{b['signature_off']:08X}.bin").write_bytes(b["data"])

    (ROOT / "logs" / "ap32_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
