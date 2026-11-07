# -*- coding: utf-8 -*-
"""闭合 U2: 预约项 +0x168/+0x16c 的写入点（这就是 mmbook 里那个 u64 的来源）。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
REGS = "eax ecx edx ebx esp ebp esi edi".split()

def scan(disp, lo=0, hi=len(d)):
    res = []
    for o in range(max(0, lo), min(len(d) - 7, hi)):
        op = d[o]
        if op not in (0x89, 0x8B):
            continue
        modrm = d[o+1]
        if (modrm >> 6) != 2 or (modrm & 7) == 4:
            continue
        v = struct.unpack_from("<i", d, o+2)[0]
        if v != disp:
            continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            res.append((op, va, modrm & 7, (modrm >> 3) & 7))
    return res

for disp in (0x168, 0x16C, 0x170):
    r = scan(disp)
    w = [x for x in r if x[0] == 0x89]
    rd = [x for x in r if x[0] == 0x8B]
    print("=== +0x%X writes=%d reads=%d ===" % (disp, len(w), len(rd)))
    for op, va, rm, src in w[:25]:
        print("   W %08X mov [%s+0x%X], %s" % (va, REGS[rm], disp, REGS[src]))
    for op, va, rm, src in rd[:15]:
        print("   R %08X mov %s, [%s+0x%X]" % (va, REGS[src], REGS[rm], disp))
