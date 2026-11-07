# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x6376E0 .. 0x637900 (second slot init + mmbook calls) ===")
for l in pe.dis(0x6376E0, 120):
    print(l)
