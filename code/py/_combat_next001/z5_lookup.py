# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0x7FA640 (the real lookup: called at 0x7FA8A8) ===")
for l in pe.dis(0x7FA640, 80):
    print(l)
