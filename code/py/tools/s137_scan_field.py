#!/usr/bin/env python3
"""s137: 扫描读取/写 [reg+disp] 的指令 (byte/dword), 用于定位结构体消费者."""
import struct
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

disp = int(sys.argv[1], 0)
kind = sys.argv[2] if len(sys.argv) > 2 else "b"   # b=byte access, d=dword
lo = int(sys.argv[3], 0) - VA if len(sys.argv) > 3 else 0
hi = int(sys.argv[4], 0) - VA if len(sys.argv) > 4 else N

print("scan disp=0x%X kind=%s VA 0x%08X..0x%08X" % (disp, kind, lo + VA, hi + VA))
res = []
for i in range(lo, min(hi, N) - 8):
    b0, b1 = d[i], d[i + 1]
    tag = None
    if kind == "b":
        # 8A /r disp8 : mov r8,[reg+disp8]
        if b0 == 0x8A and b1 >> 6 == 1 and (b1 & 7) not in (4,) and d[i + 2] == disp:
            tag = "mov r8,[r%d+0x%X]" % (b1 & 7, disp)
        # 38/3A : cmp [reg+disp8],r8 / mov r8,[reg+disp8] variant
        elif b0 in (0x38, 0x3A) and b1 >> 6 == 1 and d[i + 2] == disp:
            tag = "cmp8 [r%d+0x%X]" % (b1 & 7, disp)
        # 80 /7 ib : cmp byte [reg+disp8], imm8
        elif b0 == 0x80 and (b1 >> 3) & 7 == 7 and d[i + 2] == disp:
            tag = "cmp byte [r%d+0x%X], %d" % (b1 & 7, disp, d[i + 3])
        # C6 /0 ib : mov byte [reg+disp8], imm8
        elif b0 == 0xC6 and (b1 >> 3) & 7 == 0 and d[i + 2] == disp:
            tag = "mov byte [r%d+0x%X], %d" % (b1 & 7, disp, d[i + 3])
        # 88 /r : mov [reg+disp8], r8
        elif b0 == 0x88 and b1 >> 6 == 1 and d[i + 2] == disp:
            tag = "mov [r%d+0x%X], r8=%d" % (b1 & 7, disp, (b1 >> 3) & 7)
    else:
        if b0 == 0x8B and b1 >> 6 == 1 and d[i + 2] == disp:
            tag = "mov r%d,[r%d+0x%X]" % ((b1 >> 3) & 7, b1 & 7, disp)
        elif b0 in (0x39, 0x3B) and b1 >> 6 == 1 and d[i + 2] == disp:
            tag = "%s r%d,[r%d+0x%X]" % ("cmp" if b0 == 0x39 else "cmpr", (b1 >> 3) & 7, b1 & 7, disp)
        elif b0 == 0x83 and (b1 >> 3) & 7 == 7 and d[i + 2] == disp:
            tag = "cmp [r%d+0x%X], %d" % (b1 & 7, disp, d[i + 3])
        elif b0 == 0xC7 and (b1 >> 3) & 7 == 0 and d[i + 2] == disp:
            tag = "mov [r%d+0x%X], %d" % (b1 & 7, disp, struct.unpack_from("<i", d, i + 3)[0])
        elif b0 == 0x89 and b1 >> 6 == 1 and d[i + 2] == disp:
            tag = "mov [r%d+0x%X], r%d" % (b1 & 7, disp, (b1 >> 3) & 7)
    if tag:
        res.append((VA + i, tag, d[i:i + 8].hex()))
for va, tag, by in res:
    print("  VA 0x%08X  %-28s %s" % (va, tag, by))
print("total", len(res))
