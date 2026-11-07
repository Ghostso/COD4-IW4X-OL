# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x62F966 .. 0x62FB10 (0x62F840 path: slot index 0 + write) ===")
for l in pe.dis(0x62F966, 95):
    print(l)
