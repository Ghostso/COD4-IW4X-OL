# -*- coding: utf-8 -*-
"""017: find all 'mov byte [reg+disp32], IMM8' stores (C6 /0, mod=10) across the image."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _015_lib import BASE, DATA, END, MD

found = []
for i in range(len(DATA) - 7):
    if DATA[i] != 0xC6:
        continue
    m = DATA[i+1]
    if (m & 0xC0) != 0x80 or (m & 0x38) != 0:
        continue
    disp = struct.unpack_from("<I", DATA, i+2)[0]
    imm = DATA[i+6]
    found.append((BASE + i, disp, imm, DATA[i:i+7].hex()))
print("total 'mov byte [reg+disp32],imm8' = %d ; with imm==1 = %d"
      % (len(found), sum(1 for f in found if f[2] == 1)))
print("--- disp in {0x288, 0x278, 0x281, 0x283, 0x225, 0x4E8} ---")
for va, disp, imm, hx in found:
    if disp in (0x288, 0x278, 0x281, 0x283, 0x225, 0x4E8):
        print("  0x%08X disp=0x%-5X imm=%d  %s" % (va, disp, imm, hx))
