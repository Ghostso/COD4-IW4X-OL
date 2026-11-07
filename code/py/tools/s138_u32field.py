#!/usr/bin/env python3
"""s138_u32field: 找写 tag-8 u32 字段 (0xB766B0) 的调用点, 及其前后是否成对写两次."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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

for tgt, name in ((0xB766B0, "writeU32(tag8)"), (0xB769A0, "writeU64(tag0a)"),
                   (0xB765E0, "writeBool(tag1)"), (0xB76620, "writeU8(tag3)")):
    cs = callers(tgt)
    print("=== callers of 0x%08X %s : %d ===" % (tgt, name, len(cs)))
    for c in cs:
        print("   call@VA 0x%08X" % (VA + c))
