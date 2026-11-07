# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0xBA74B0 (called at 0xB9B1C1 with [ebp+0x18] = param5) ===")
for l in pe.dis(0xBA74B0, 60):
    print(l)
print()
print("=== 0xBA72C0 (constructs the message object at [ebp-0x44]) ===")
for l in pe.dis(0xBA72C0, 45):
    print(l)
