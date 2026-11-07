# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0xB9B0B0 (called by the registrar with the callback) ===")
for l in pe.dis(0xB9B0B0, 70):
    print(l)
print()
print("=== callers of 0x7FAA20 / 0x7FAAB0 / 0x7F44B0 counts ===")
for t in (0x7FAA20, 0x7FAAB0, 0x7F44B0, 0x7F44B0):
    print("   0x%08X -> %d" % (t, len(pe.calls_to(t))))
print()
print("=== the other registrar caller: 0x62932F context ===")
for l in pe.dis(0x629310, 20):
    print(l)
