# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x675260 (called with getchallenge string) ===")
for l in pe.dis(0x675260, 80):
    print(l)
