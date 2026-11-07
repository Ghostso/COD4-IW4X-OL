# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

for vtb in (0xDC72B0, 0xDC7750):
    print("=== vtable at 0x%08X (slots) ===" % vtb)
    for i in range(0, 24):
        v = struct.unpack("<I", pe.read(vtb + i*4, 4))[0]
        tag = ""
        if v == 0x62F840: tag = "  <- accepted/battle-booking entry (0x278 gate)"
        if v == 0x62CD30: tag = "  <- RESERVATION SLOT FILLER"
        if v == 0x632680: tag = "  <- mmbook accepted handler"
        if v == 0x6376F0: tag = "  <- slot filler entry (0x637590)"
        print("   [%2d] +0x%02X  %08X%s" % (i, i*4, v, tag))
    print()

print("=== indirect calls to vtable slot +0x08  (call dword ptr [reg+8]) ===")
d = pe.data
n = 0
for o in range(len(d) - 3):
    if d[o] == 0xFF and d[o+1] == 0x50 and d[o+2] == 0x08:
        va = pe.off_to_va(o)
        if va and pe.is_exec(va):
            n += 1
            if n <= 25: print("   %08X" % va)
print("   total =", n)
