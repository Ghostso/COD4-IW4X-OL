# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x7F1200 .. 0x7F1500 (dispatcher: where mmbook command comes from) ===")
for l in pe.dis(0x7F1200, 150):
    print(l)
