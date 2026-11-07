# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== context of data-ref to 0x6376F0 at 0x62DDEA ===")
for l in pe.dis(0x62DDD0, 22):
    print(l)
print()
print("=== context of data-ref to 0x6376F0 at 0x7F4478 ===")
for l in pe.dis(0x7F4460, 22):
    print(l)
