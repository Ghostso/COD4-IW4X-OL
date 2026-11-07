# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
for va, nm in ((0xB9A12F, "0xB9A12F"), (0xB9A19F, "0xB9A19F"), (0xB9A36F, "0xB9A36F"),
               (0xBACE1F, "0xBACE1F"), (0xBACF4F, "0xBACF4F"), (0xC2D80F, "0xC2D80F"),
               (0x848FEF, "0x848FEF")):
    print("=" * 70)
    print("=== %s (function containing the +0x168 write) ===" % nm)
    for l in pe.dis(va, 26):
        print(l)
    print()
