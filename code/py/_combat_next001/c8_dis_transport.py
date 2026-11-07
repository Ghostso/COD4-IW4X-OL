# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x6751F0 (transport) ===")
for l in pe.dis(0x6751F0, 90):
    print(l)
print()
print("=== calls to 0x6751F0 ===")
for va in pe.calls_to(0x6751F0):
    print("   %08X" % va)
