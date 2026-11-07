#!/usr/bin/env python3
"""s138_callers_text: 只在 .text 内找 call rel32 到目标 (排除数据区假阳性)."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000 - VA, 0x401000 + 0x8a689a - VA   # file offsets

def callers(tgt):
    res = []
    t = tgt - VA
    for i in range(TL, min(TH, N - 5)):
        if d[i] == 0xE8:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if (i + VA + 5 + rel) & 0xFFFFFFFF == tgt & 0xFFFFFFFF:
                res.append(i)
    return res

def ptrs(tgt):
    pat = struct.pack("<I", tgt)
    out = []; i = TL
    while True:
        j = d.find(pat, i, TH)
        if j < 0: break
        out.append(j); i = j + 1
    return out

for tgt in [0x7E7C90, 0x7E7A30, 0x6371F0, 0x637000, 0x634870, 0x6256C0]:
    cs = callers(tgt)
    ps = ptrs(tgt)
    print("0x%08X  calls=%s ptrs=%s" % (tgt, [hex(VA+c) for c in cs], [hex(VA+p) for p in ps[:8]]))
