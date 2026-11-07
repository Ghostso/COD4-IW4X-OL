# -*- coding: utf-8 -*-
"""对齐感知的筛查：只保留在合法函数体内部、且指令边界自洽的候选。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
REGS = "eax ecx edx ebx esp ebp esi edi".split()

def func_start(va):
    for back in range(1, 0x900):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC:
            return x + 1
    return None

def dis_contains(target_va, start=None, count=40):
    """从 start 反汇编，看是否恰好落在 target_va 上（用于判断对齐）。"""
    md = pe._md()
    if start is None:
        start = func_start(target_va)
    if start is None:
        return False, None
    code = pe.data[start - pe.base:]
    n = 0
    last = None
    for ins in md.disasm(code, start):
        if ins.address == target_va:
            return True, last
        if ins.address > target_va:
            return False, last
        last = ins.address
        n += 1
        if n > 300:
            break
    return False, last

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

print("%-4s %-9s %-9s %-9s %-6s %-6s %s" % ("#", "A_va", "B_va", "func", "alignA", "alignB", "note"))
good = []
for i, (va, va2) in enumerate(pairs, 1):
    fs = func_start(va)
    okA, prevA = dis_contains(va, fs)
    okB, prevB = dis_contains(va2, fs)
    note = ""
    if okA and okB:
        good.append((i, va, va2, fs))
        note = "ALIGNED"
    print("%-4d %08X %08X %-9s %-6s %-6s %s" % (
        i, va, va2, ("%08X" % fs) if fs else "-", okA, okB, note))
print()
print("aligned candidates = %d" % len(good))
for i, va, va2, fs in good:
    print("   [%d] %08X / %08X  func %08X" % (i, va, va2, fs))
