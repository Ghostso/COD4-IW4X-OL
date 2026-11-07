# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x7FAA20 (the registry/activator) ===")
for l in pe.dis(0x7FAA20, 90):
    print(l)
