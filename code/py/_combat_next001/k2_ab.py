# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== 0x62F6C0 (called from accepted handler 0x632812) : is this the A/B reset? ===")
for l in pe.dis(0x62F6C0, 45):
    print(l)
print()
print("=== context of the A/B WRITERS 0x62F717 / 0x62F73C (and reader 0x62F7F9) ===")
for l in pe.dis(0x62F6E0, 80):
    print(l)
