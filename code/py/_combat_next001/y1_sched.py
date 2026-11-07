# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x6292B0 (the deferred scheduler: callers pass 0x637930) ===")
for l in pe.dis(0x6292B0, 60):
    print(l)
print()
print("=== callers of 0x6292B0 ===")
for v in pe.calls_to(0x6292B0):
    print("   %08X" % v)
print()
print("=== 0x637AB0 (called at 0x62FBB0 with [esi+0x105f0], [ebp+8]) ===")
for l in pe.dis(0x637AB0, 40):
    print(l)
