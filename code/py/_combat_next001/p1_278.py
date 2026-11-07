# -*- coding: utf-8 -*-
"""U1: [reg+0x278] 的所有读写点，按 4 字节 disp32 形式。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
REGS = "eax ecx edx ebx esp ebp esi edi".split()

def scan(disp):
    res = []
    for o in range(len(d) - 7):
        op = d[o]
        if op not in (0x88, 0x89, 0x8A, 0x8B, 0x8D):
            continue
        m = d[o+1]
        if (m >> 6) != 2 or (m & 7) == 4:
            continue
        v = struct.unpack_from("<i", d, o+2)[0]
        if v != disp:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            res.append((op, va, m & 7, (m >> 3) & 7))
    return res

print("=== +0x278: 全部 disp32 访问 ===")
for op, va, rm, src in sorted(scan(0x278), key=lambda x: x[1]):
    nm = {0x88:"mov b [..],r",0x89:"mov d [..],r",0x8A:"mov r,[..]b",0x8B:"mov r,[..]d",0x8D:"lea"}[op]
    if op == 0x8D:
        print("   LEA %08X  %s <- [%s+0x278]" % (va, REGS[src], REGS[rm]))
    elif op in (0x88, 0x89):
        print("   W   %08X  [%s+0x278] <- %s   (%s)" % (va, REGS[rm], REGS[src], nm))
    else:
        print("   R   %08X  %s <- [%s+0x278]   (%s)" % (va, REGS[src], REGS[rm], nm))
