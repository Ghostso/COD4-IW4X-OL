# -*- coding: utf-8 -*-
"""Offline candidate: keep the real engine sections and replace the protection
tail with a minimal import/entry stub. Writes only under work/."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe")
OUT = ROOT / "work" / "candidate_stub.exe"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    src = SRC.read_bytes()
    d = bytearray(src[:0x771000])
    e = struct.unpack_from("<I", d, 0x3C)[0]
    opt = e + 24
    opt_size = struct.unpack_from("<H", d, e + 20)[0]
    sec = opt + opt_size
    nsec = struct.unpack_from("<H", d, e + 6)[0]
    rows = []
    for i in range(nsec):
        o = sec + i * 40
        name = bytes(d[o:o + 8]).rstrip(b"\0").decode("latin-1")
        vs, va, rs, ro = struct.unpack_from("<IIII", d, o + 8)
        rows.append((name, va, vs, ro, rs, o))
    last = rows[-1]
    tvm = rows[-2]
    print("kept", rows[:-1])
    print("removed", last)

    # Make the last section a minimal bootstrap section.
    stub_raw = 0x1000
    stub_va = tvm[1] + 0x4000       # right after .tvm0, before old tail
    stub_rva = stub_va
    stub = bytearray(stub_raw)
    struct.pack_into("<I", d, last[5] + 8, 0x400)           # virtual size
    struct.pack_into("<I", d, last[5] + 12, stub_va)
    struct.pack_into("<I", d, last[5] + 16, stub_raw)
    struct.pack_into("<I", d, last[5] + 20, 0x771000)
    struct.pack_into("<I", d, last[5] + 36, 0xE0000020)
    struct.pack_into("<Q", stub, 0, 0x4770656E6420474C)   # "GL dnegpG" placeholder
    # Stub only: entry jumps to a Base.dll reload path patched later into this section.
    # Uses no external symbols until the loader work is added.
    struct.pack_into("<I", d, opt + 16, stub_rva)           # AddressOfEntryPoint = stub
    sect_align = struct.unpack_from("<I", d, opt + 32)[0]
    size_image = (stub_va + struct.unpack_from("<I", d, last[5] + 8)[0] + sect_align - 1) // sect_align * sect_align
    struct.pack_into("<I", d, opt + 56, size_image)
    d.extend(stub)
    OUT.write_bytes(d)
    print(f"stub_va=0x{stub_va:X} SizeOfImage=0x{size_image:X} file={len(d)} sha={sha(d)}")
    (ROOT / "logs" / "stub_candidate.json").write_text(json.dumps({
        "source_sha256": sha(src), "candidate_sha256": sha(d),
        "stub_rva": stub_va, "size_of_image": size_image,
        "removed_tail": last[1:5], "path": str(OUT),
    }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
