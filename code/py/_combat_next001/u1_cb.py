# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0xB9B0B0 : full function, find indirect calls & buffer use ===")
lines = pe.dis(0xB9B0B0, 200)
for l in lines:
    print(l)
