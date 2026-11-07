#!/usr/bin/env python3
"""s138_writers: 找调用 TLV 类型写函数 (0xB75F30 / 0xB76310) 的所有点, 看 push 的 tag 值."""
import struct, sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

def callers(tgt):
    res = []
    for i in range(N - 5):
        if d[i] == 0xE8:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if (i + VA + 5 + rel) & 0xFFFFFFFF == tgt:
                res.append(i)
    return res

md = Cs(CS_ARCH_X86, CS_MODE_32)
for tgt in (0xB75F30, 0xB76310):
    print("=== callers of 0x%08X ===" % tgt)
    for c in callers(tgt)[:60]:
        # look back 12 bytes for push imm8
        seg = d[max(0, c-12):c]
        tag = None
        for k in range(len(seg)-1):
            if seg[k] == 0x6A:
                tag = seg[k+1]
        print("  call@VA 0x%08X  prevbytes=%s  push_imm=%s" % (
            VA+c, seg.hex(), tag))
