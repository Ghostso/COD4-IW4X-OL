# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0xC7B8F0 (called with udp:// uri + addr) ===")
for l in pe.dis(0xC7B8F0, 70):
    print(l)
print()
print("=== callers ===")
for va in pe.calls_to(0xC7B8F0):
    print("   %08X" % va)
