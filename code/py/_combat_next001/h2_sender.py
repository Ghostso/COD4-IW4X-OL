# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x771320 (called with 0x849b87c and 0) ===")
for l in pe.dis(0x771320, 70):
    print(l)
print()
print("=== callers count ===")
c = pe.calls_to(0x771320)
print("  %d callers" % len(c))
