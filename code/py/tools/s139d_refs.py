#!/usr/bin/env python3
"""139d: 找 0x7F1060/0x7F1040/0x7F10C0 的调用者与 vtable 引用；
以及 0x7E7EE0/0x633FE0/0x633DF0/0x7E8120 的调用者。
"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IMG = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(IMG, "rb").read()

def callers(t):
    out = []
    for i in range(len(d) - 5):
        if d[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", d, i + 1)[0]
        if i + 5 + rel + VA == t:
            out.append(hex(i + VA))
    return out

def drefs(t):
    p = struct.pack("<I", t)
    i, hits = 0, []
    while True:
        j = d.find(p, i)
        if j < 0:
            break
        hits.append(hex(j + VA))
        i = j + 1
    return hits

for t in (0x7F1060, 0x7F1040, 0x7F10C0, 0x7E7EE0, 0x633FE0, 0x633DF0,
          0x7E7FB0, 0x7E8120, 0x803830, 0xB7A770):
    print(f"\n0x{t:08X}")
    print("  E8 callers :", callers(t))
    dr = drefs(t)
    print(f"  dword refs : {len(dr)} ->", dr[:20])
