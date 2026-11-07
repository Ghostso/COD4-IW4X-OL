# -*- coding: utf-8 -*-
"""枚举 0x7230 / 0x7238 / 0xE360 / 0x7470 的全部 disp32 访问，定位预约系统的入口集。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R = "eax ecx edx ebx esp ebp esi edi".split()

def scan(disp, ops):
    res = []
    for o in range(len(d) - 7):
        if d[o] not in ops: continue
        m = d[o+1]
        if (m >> 6) != 2 or (m & 7) == 4: continue
        if struct.unpack_from("<i", d, o+2)[0] != disp: continue
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            res.append((d[o], va, m & 7, (m >> 3) & 7))
    return res

def func(va):
    for back in range(1, 0x1200):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

for disp, label in ((0x7230, "slot COUNT"), (0x7238, "slot count mirror?"), (0xE360, "slot INDEX")):
    print("=== +0x%X (%s) — writes ===" % (disp, label))
    for op, va, rm, src in sorted(scan(disp, (0x88,0x89,0xC6,0xC7))):
        kind = "imm" if op in (0xC6,0xC7) else R[src]
        imm = ""
        if op in (0xC6,0xC7):
            immv = struct.unpack_from("<I", d, pe.va_to_off(va)+ (6 if op==0xC7 else 6))[0]
            imm = " imm=0x%X" % immv
        print("   %08X  [%s+0x%X] <- %s%s   (func ~%s)" % (va, R[rm], disp, kind, imm, ("%08X"%func(va)) if func(va) else "?"))
    print()
