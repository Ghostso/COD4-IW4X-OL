# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0x62F840 full body ===")
for l in pe.dis(0x62F840, 80):
    print(l)
