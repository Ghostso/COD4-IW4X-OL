# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== caller 1: 0x62F917 context ===")
for l in pe.dis(0x62F8D0, 45):
    print(l)
print()
print("=== callers 2/3: 0x63789D / 0x6378BE context ===")
for l in pe.dis(0x637860, 45):
    print(l)
