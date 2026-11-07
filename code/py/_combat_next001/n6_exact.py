# -*- coding: utf-8 -*-
"""直接搜 [reg+0x75D8] / [reg+0x75DC] 的读写点（预约槽 +0x168/+0x16C 的对象相对地址）。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
REGS = "eax ecx edx ebx esp ebp esi edi".split()

def scan(disp, op):
    out = []
    for o in range(len(d) - 7):
        if d[o] != op:
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

for disp in (0x75D8, 0x75DC, 0x75E0, 0x7470):
    print("=== disp 0x%X ===" % disp)
    for op, nm in ((0x89, "W"), (0x8B, "R"), (0x8D, "LEA")):
        for va, rm, src in scan(disp, op):
            if op == 0x89:
                print("   %s %08X  mov [%s+0x%X], %s" % (nm, va, REGS[rm], disp, REGS[src]))
            elif op == 0x8B:
                print("   %s %08X  mov %s, [%s+0x%X]" % (nm, va, REGS[src], REGS[rm], disp))
            else:
                print("   %s %08X  lea %s, [%s+0x%X]" % (nm, va, REGS[src], REGS[rm], disp))
    print()
