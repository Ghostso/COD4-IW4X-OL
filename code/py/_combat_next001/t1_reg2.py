# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x7F44B0 (registrar used by 0x62DDF4) ===")
for l in pe.dis(0x7F44B0, 70):
    print(l)
print()
print("=== callers of 0x7F44B0 ===")
c = pe.calls_to(0x7F44B0)
print("   count = %d" % len(c))
for v in c[:20]:
    print("      %08X" % v)
