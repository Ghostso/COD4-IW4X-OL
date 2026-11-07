#!/usr/bin/env python3
"""capstone 反汇编:
A) 0x240F60..0x2412E0 (UIPage/UIClick 两个函数的完整体 + 共用 helper)
B) helper 0x240FD0 的被调 0x2571D0 (发射器) 及其调用面
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def cstr(off, maxlen=200):
    if not (0 <= off < N): return None
    e = d.find(b"\x00", off)
    if e < 0 or e - off > maxlen: e = off + maxlen
    return d[off:e]

def annotate(ins):
    # 立即数若落进 VA 且是串, 注释
    for op in ins.operands:
        pass
    return ""

def dis(start, length, title):
    print("=" * 78)
    print(title)
    print("=" * 78)
    code = d[start:start + length]
    for ins in md.disasm(code, start + VA):
        line = "  0x%08X  %-28s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        # 注解: 找操作数里的 0x... 立即数
        import re
        for m in re.finditer(r"0x([0-9a-f]{6,8})", ins.op_str):
            v = int(m.group(1), 16)
            if VA <= v < VA + N:
                s = cstr(v - VA, 80)
                if s and all(32 <= c < 127 or c in (9, 10) for c in s):
                    line += "   ; %r" % s.decode("latin1")
        print(line)

a = int(__import__("sys").argv[1], 0) if len(__import__("sys").argv) > 1 else 0x240F60
L = int(__import__("sys").argv[2], 0) if len(__import__("sys").argv) > 2 else 0x380
dis(a, L, "disasm @file 0x%06X" % a)
