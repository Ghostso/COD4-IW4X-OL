# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x621E50 (endpoint writer per 007/014) ===")
for l in pe.dis(0x621E50, 90):
    print(l)
