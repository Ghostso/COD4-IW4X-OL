# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x5C06C0..0x5C0A00 (getchallenge + natType site) ===")
for l in pe.dis(0x5C06C0, 190):
    print(l)
