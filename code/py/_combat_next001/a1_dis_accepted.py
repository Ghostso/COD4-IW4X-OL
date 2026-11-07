# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE

pe = PE.load()
print("=== 0x632680 accepted handler (60 insns) ===")
for l in pe.dis(0x632680, 60):
    print(l)
