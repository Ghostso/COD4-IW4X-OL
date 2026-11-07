# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
R32 = ["eax","ecx","edx","ebx","esp","ebp","esi","edi"]

print("=== all 'call dword ptr [reg+0x08]' (FF /2, mod=01, rm!=4) ===")
n = 0
for o in range(len(d) - 3):
    if d[o] != 0xFF: continue
    m = d[o+1]
    if (m & 0x38) != 0x10: continue          # /2 = call
    if (m >> 6) != 1: continue               # mod=01 -> disp8
    rm = m & 7
    if rm == 4: continue
    if d[o+2] != 0x08: continue
    va = pe.off_to_va(o)
    if va and pe.is_exec(va):
        n += 1
        if n <= 40:
            print("   %08X  call [%s+0x08]" % (va, R32[rm]))
print("   total =", n)
print()
print("=== all 'call dword ptr [reg+0x08]' with SIB (FF /2 mod=01 rm=4) ===")
n2 = 0
for o in range(len(d) - 4):
    if d[o] != 0xFF: continue
    m = d[o+1]
    if (m & 0x38) != 0x10 or (m >> 6) != 1 or (m & 7) != 4: continue
    if d[o+3] != 0x08: continue
    va = pe.off_to_va(o)
    if va and pe.is_exec(va):
        n2 += 1
        if n2 <= 20: print("   %08X" % va)
print("   total =", n2)
