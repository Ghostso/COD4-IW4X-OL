# -*- coding: utf-8 -*-
"""Build an offline candidate image with the protection tail section removed.

Writes only under STRIP_PROTECTION_001/work. The retail file is never touched.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe")
OUT = ROOT / "work" / "candidate_no_guard.exe"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    data = bytearray(SRC.read_bytes())
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    opt_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    opt = e_lfanew + 24
    sec_tab = opt + opt_size

    rows = []
    for i in range(nsec):
        o = sec_tab + i * 40
        name = bytes(data[o:o + 8]).rstrip(b"\0").decode("latin-1")
        vs, va, rs, ro = struct.unpack_from("<IIII", data, o + 8)
        chars = struct.unpack_from("<I", data, o + 36)[0]
        rows.append({"i": i, "name": name, "va": va, "vs": vs,
                     "raw": ro, "raw_size": rs, "chars": chars})
    print(json.dumps(rows, indent=2))

    old_image = struct.unpack_from("<I", data, opt + 56)[0]
    print(f"old SizeOfImage=0x{old_image:X}")

    # Drop the final section (.tp3, the TenProtect carrier) from the section table.
    last = rows[-1]
    new_nsec = nsec - 1
    struct.pack_into("<H", data, e_lfanew + 6, new_nsec)

    # New SizeOfImage = end of the previous section, rounded to FileAlignment.
    prev = rows[-2]
    end = prev["va"] + prev["vs"]
    sect_align = struct.unpack_from("<I", data, opt + 32)[0]
    new_image = (end + sect_align - 1) // sect_align * sect_align
    struct.pack_into("<I", data, opt + 56, new_image)
    print(f"cut section #{last['i']} {last['name']} va=0x{last['va']:X} "
          f"vsize=0x{last['vs']:X} raw=0x{last['raw']:X} raw_size=0x{last['raw_size']:X}")
    print(f"new SizeOfImage=0x{new_image:X}")

    # Truncate the file to the end of the previous section's raw data.
    cut_at = prev["raw"] + prev["raw_size"]
    out = bytes(data[:cut_at])
    OUT.write_bytes(out)
    print(f"wrote {OUT} size={len(out)} sha256={sha(out)}")

    (ROOT / "logs" / "candidate.json").write_text(json.dumps({
        "source": str(SRC), "source_sha256": sha(SRC.read_bytes()),
        "candidate": str(OUT), "candidate_sha256": sha(out),
        "removed_section": last, "old_size_of_image": old_image,
        "new_size_of_image": new_image, "cut_at": cut_at,
    }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
