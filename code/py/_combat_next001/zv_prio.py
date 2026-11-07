# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
for f, nm in ((0x7F343F, "0x7F343F (0x238 x2)"), (0xBAD24F, "0xBAD24F (0x238)")):
    print("=" * 72)
    print("=== %s ===" % nm)
    for l in pe.dis(f, 60):
        print(l)
    print()
