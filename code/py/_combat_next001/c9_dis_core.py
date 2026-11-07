# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x6750A0 (packet send core) ===")
for l in pe.dis(0x6750A0, 110):
    print(l)
print()
print("=== callers of 0x6750A0 ===")
for va in pe.calls_to(0x6750A0):
    print("   %08X" % va)
