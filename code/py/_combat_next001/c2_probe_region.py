# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
for va in (0x5C06C0, 0x5C0710, 0x5C0900, 0x5C0920, 0x5C0940):
    b = pe.read(va, 32)
    print("%08X: %s" % (va, b.hex() if b else "(no data)"))
print()
print("=== dis from 0x5C0700 ===")
for l in pe.dis(0x5C0700, 40):
    print(l)
print()
print("=== dis from 0x5C0910 ===")
for l in pe.dis(0x5C0910, 25):
    print(l)
