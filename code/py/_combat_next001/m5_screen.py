# -*- coding: utf-8 -*-
"""筛查 21 组成对写入点：打印每处的前后各 14 条指令与所属函数。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
REGS = "eax ecx edx ebx esp ebp esi edi".split()

def scan(disp):
    out = []
    for o in range(len(d) - 7):
        if d[o] != 0x89:
            continue
        m = d[o+1]
        if (m >> 6) != 2 or (m & 7) == 4:
            continue
        v = struct.unpack_from("<i", d, o+2)[0]
        if v != disp:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            out.append((va, m & 7, (m >> 3) & 7))
    return out

pairs = []
for va, rm, src in scan(0x168):
    for va2, rm2, src2 in scan(0x16C):
        if 0 < va2 - va <= 0x40:
            pairs.append((va, va2)); break

def func_start(va):
    for back in range(1, 0x900):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC:
            return x + 1
    return None

lines = []
for i, (va, va2) in enumerate(pairs, 1):
    fs = func_start(va)
    lines.append("=" * 78)
    lines.append("[%2d] pair %08X / %08X   (function ~%s)" % (
        i, va, va2, ("%08X" % fs) if fs else "?"))
    lines.append("-" * 78)
    for l in pe.dis(max(0, va - 0x28), 22):
        lines.append("   " + l)
out = "\n".join(lines)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "m5_pairs.txt"),
     "w", encoding="utf-8").write(out)
print(out[:6000])
print()
print("... full listing written to m5_pairs.txt (%d lines)" % len(lines))
