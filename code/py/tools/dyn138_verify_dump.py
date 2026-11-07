#!/usr/bin/env python3
"""138 · 离线复核转存: 在 DUMP 目录里按 VA 取值（证明转存可用）。
用法: python -X utf8 tools\dyn138_verify_dump.py <dumpdir> [VA...]
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

dump = sys.argv[1]
vas = [int(x, 0) for x in sys.argv[2:]] or [
    0x0849BA30, 0x0849BA34, 0x084ABA50, 0x00E59D20,
    0x082E13FC, 0x08269774, 0x0E7B8644, 0x0331D408, 0x033303B0, 0x0C911F60,
]
regs = []
with open(os.path.join(dump, "regions.txt"), encoding="utf-8", errors="replace") as f:
    for ln in f:
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if len(p) >= 3:
            regs.append((int(p[0], 16), int(p[1], 16), p[2]))
print("区域数 %d" % len(regs))


def readva(va, n=4):
    for base, size, fn in regs:
        if base <= va < base + size:
            try:
                with open(os.path.join(dump, "mem", fn), "rb") as f:
                    f.seek(va - base)
                    return f.read(n)
            except OSError:
                return None
    return None


for va in vas:
    d = readva(va)
    print("  %08X = %s" % (va, (struct.unpack("<I", d)[0] if d and len(d) == 4 else d)))
