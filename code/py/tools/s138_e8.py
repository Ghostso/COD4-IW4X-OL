#!/usr/bin/env python3
"""s138_e8: fast E8-caller finder for many targets in one pass.
usage: python -I tools\\s138_e8.py 0x62A100 0x...
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
CODE_OFF, CODE_SZ = 0x1000, 0x8A7000

targets = {}
for a in sys.argv[1:]:
    targets[int(a, 0)] = []

seg = d[CODE_OFF:CODE_OFF + CODE_SZ]
for i in range(len(seg) - 5):
    if seg[i] == 0xE8:
        rel = struct.unpack_from("<i", seg, i + 1)[0]
        t = (VA + CODE_OFF + i + 5 + rel) & 0xFFFFFFFF
        if t in targets:
            targets[t].append(VA + CODE_OFF + i)

for t, cs in targets.items():
    print("== 0x%08X : %d callers ==" % (t, len(cs)))
    for c in cs:
        print("   0x%08X" % c)
