# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x7FA800 tail (0x7FA920 .. 0x7FAA20) : entry consumption / dispatch ===")
for l in pe.dis(0x7FA920, 90):
    print(l)
