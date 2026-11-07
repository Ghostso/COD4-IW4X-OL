#!/usr/bin/env python3
"""s137: 扫描镜像里读取 [reg+0x14] 的指令 (cmp/mov/test), 限定 VA 范围."""
import struct
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

lo = int(sys.argv[1], 0) - VA if len(sys.argv) > 1 else 0
hi = int(sys.argv[2], 0) - VA if len(sys.argv) > 2 else N
disp = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x14

MODRM_LO = {0x00: 0x40, 0x01: 0x40}  # placeholder

def rn(b):
    return (b >> 3) & 7

print("scan VA 0x%08X..0x%08X disp=0x%X" % (lo + VA, hi + VA, disp))
hits = 0
for i in range(lo, min(hi, N) - 8):
    b0, b1, b2 = d[i], d[i + 1], d[i + 2]
    tag = None
    # 83 /7 ib  : cmp dword [reg+disp8], imm8
    if b0 == 0x83 and b2 == disp and (b1 & 0xF8) == 0x78:
        tag = "cmp [r%d+0x%X], %d" % (b1 & 7, disp, d[i + 3])
    # 81 /7 id  : cmp dword [reg+disp32], imm32
    elif b0 == 0x81 and (b1 & 0xF8) == 0xB8:
        dd = struct.unpack_from("<I", d, i + 2)[0]
        if dd == disp:
            tag = "cmp [r%d+0x%X], %d" % (b1 & 7, disp, struct.unpack_from("<i", d, i + 6)[0])
    # 8B /r disp8 : mov r32,[reg+disp8]
    elif b0 == 0x8B and b2 == disp and (b1 & 0xC0) == 0x40:
        tag = "mov r%d,[r%d+0x%X]" % (rn(b1), b1 & 7, disp)
    # 8B /r disp32
    elif b0 == 0x8B and (b1 & 0xC0) == 0x80:
        dd = struct.unpack_from("<I", d, i + 2)[0]
        if dd == disp:
            tag = "mov r%d,[r%d+0x%X]" % (rn(b1), b1 & 7, disp)
    # 39/3B /r disp8 : cmp [reg+disp8], reg / cmp reg,[...]
    elif b0 in (0x39, 0x3B) and b2 == disp and (b1 & 0xC0) == 0x40:
        tag = "%s r%d,[r%d+0x%X]" % ("cmp" if b0 == 0x39 else "cmpr", rn(b1), b1 & 7, disp)
    # F7 4? disp8 ... test
    elif b0 == 0xF7 and b2 == disp and (b1 & 0xF8) == 0x40:
        tag = "test [r%d+0x%X], %d" % (b1 & 7, disp, struct.unpack_from("<i", d, i + 3)[0])
    if tag:
        hits += 1
        print("  VA 0x%08X  %-28s  bytes=%s" % (VA + i, tag, d[i:i + 8].hex()))
print("total", hits)
