# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x5C0820 .. 0x5C0A20 ===")
for l in pe.dis(0x5C0820, 130):
    print(l)
