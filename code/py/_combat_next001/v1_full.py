# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0xB9B0B0 : full disassembly (all lines) ===")
for l in pe.dis(0xB9B0B0, 110):
    print(l)
