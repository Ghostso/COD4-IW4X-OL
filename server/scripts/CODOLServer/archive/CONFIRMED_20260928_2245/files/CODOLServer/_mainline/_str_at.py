#!/usr/bin/env python3
"""Read NUL-terminated ASCII strings from the decrypted runtime image by VA.

Usage:
  python -X utf8 CODOLServer/_mainline/_str_at.py 0xD5A0E8 0xD5A0FC 0xD5A114
  python -X utf8 CODOLServer/_mainline/_str_at.py --range 0xD5A0D0:0xD5A1C0
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(HERE, "_dyn100_run_20260925_182324", "live",
                     "image_best.bin")
BASE = 0x400000

with open(IMAGE, "rb") as _fh:
    DATA = _fh.read()


def read_str(va: int, limit: int = 120) -> str:
    off = va - BASE
    if not (0 <= off < len(DATA)):
        return "<out of image>"
    end = DATA.find(b"\x00", off, off + limit)
    if end < 0:
        end = off + limit
    raw = DATA[off:end]
    out = []
    for b in raw:
        out.append(chr(b) if 0x20 <= b < 0x7F else ".")
    return "".join(out)


def main(argv: list) -> int:
    if argv and argv[0] == "--range":
        lo_s, _, hi_s = argv[1].partition(":")
        lo, hi = int(lo_s, 16), int(hi_s, 16)
        va = lo
        while va < hi:
            s = read_str(va, 200)
            if s and s != "<out of image>" and s.strip("."):
                print("0x%08X  %s" % (va, s))
                va += max(1, len(s) + 1)
            else:
                va += 1
        return 0

    for spec in argv:
        va = int(spec, 16)
        print("0x%08X  %s" % (va, read_str(va)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
