# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x637440 .. 0x6375A0 (callers of the +0x278 setter) ===")
for l in pe.dis(0x637440, 90):
    print(l)
