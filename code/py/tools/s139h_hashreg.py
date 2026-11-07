# -*- coding: utf-8 -*-
"""139h: 找 0xB7F950(哈希插入) 的调用者，并在调用点前后抽取 push imm32（名字/类型号）。"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IMG = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(IMG, "rb").read()

def callers(t):
    out = []
    for i in range(len(d) - 5):
        if d[i] == 0xE8 and (i + 5 + struct.unpack_from("<i", d, i + 1)[0] + VA) == t:
            out.append(i + VA)
    return out

def cstr(va):
    o = va - VA
    if o < 0 or o >= len(d):
        return None
    e = d.find(b"\0", o, o + 64)
    if e < 0:
        return None
    s = d[o:e]
    if all(32 <= b < 127 for b in s) and s:
        return s.decode()
    return None

cs = callers(0xB7F950)
print(f"0xB7F950 调用者 {len(cs)} 个: {[hex(x) for x in cs]}")
for c in cs:
    print(f"\n--- 调用点 0x{c:08X} 前 0x60 字节 ---")
    lo = c - 0x60
    for i in range(lo, c + 6):
        b = d[i - VA]
        if b in (0x68,):  # push imm32
            imm = struct.unpack_from("<I", d, i + 1 - VA)[0]
            s = cstr(imm)
            print(f"  0x{i:08X}  push 0x{imm:08X}  {('<'+s+'>') if s else ''}")
        elif b == 0x6A:   # push imm8
            print(f"  0x{i:08X}  push {d[i+1-VA]}")
