# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x632790 .. 0x6328F0 (accepted state writes + listener loop) ===")
for l in pe.dis(0x632790, 70):
    print(l)
print()
print("=== 0x6328F0 .. 0x632960 (failure tail) ===")
for l in pe.dis(0x6328e5, 25):
    print(l)
