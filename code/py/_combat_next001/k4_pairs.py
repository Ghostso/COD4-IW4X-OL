# -*- coding: utf-8 -*-
"""找出同时写 +0x168 与 +0x16C 的候选（A/B 成对写入点）。"""
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

a = dict((x[0], x) for x in scan(0x168))
b = dict((x[0], x) for x in scan(0x16C))
print("=== pairs writing +0x168 and +0x16C within 0x40 bytes ===")
cands = []
for va in sorted(a):
    for va2, rm2, src2 in scan(0x16C):
        if 0 < va2 - va <= 0x40:
            cands.append((va, va2))
            print("   %08X mov [%s+0x168], %s   /   %08X mov [%s+0x16C], %s" % (
                va, REGS[a[va][1]], REGS[a[va][2]], va2, REGS[rm2], REGS[src2]))
            break
print()
print("=== enclosing functions of those candidates ===")
for va, va2 in cands:
    for back in range(1, 0x900):
        x = va - back
        bb = pe.read(x, 2)
        if bb and bb[0] == 0xCC and bb[1] == 0xCC:
            print("   pair %08X/%08X inside function ~%08X" % (va, va2, x + 1))
            break
