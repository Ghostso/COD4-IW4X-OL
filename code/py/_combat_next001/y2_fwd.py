# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x637930 (thin forwarder) ===")
for l in pe.dis(0x637930, 14):
    print(l)
print()
print("=== 0x637720 (the slot WRITER it forwards to) head ===")
for l in pe.dis(0x637720, 40):
    print(l)
