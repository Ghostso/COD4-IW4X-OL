#!/usr/bin/env python3
"""137: xref - find call/jmp sites (e8/e9 rel32) targeting a VA."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def callers(target):
    out = []
    for op in (0xE8, 0xE9):
        pos = 0
        while True:
            i = d.find(bytes([op]), pos)
            if i < 0 or i + 5 > N:
                break
            pos = i + 1
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if VA + i + 5 + rel == target:
                out.append((VA + i, "call" if op == 0xE8 else "jmp"))
    return out


for a in sys.argv[1:]:
    t = int(a, 0)
    cs = callers(t)
    print("target 0x%08X : %d refs" % (t, len(cs)))
    for va, k in cs:
        f = va - VA
        print("   0x%08X  %s  ctx=%s" % (va, k, d[f - 8:f + 8].hex(" ")))
