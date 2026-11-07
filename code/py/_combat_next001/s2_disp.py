# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x7FA800 (real dispatcher called by 0x7FAA20) ===")
for l in pe.dis(0x7FA800, 90):
    print(l)
print()
print("=== callers of 0x7FA800 ===")
c = pe.calls_to(0x7FA800)
print("   count = %d" % len(c))
for v in c[:20]:
    print("      %08X" % v)
