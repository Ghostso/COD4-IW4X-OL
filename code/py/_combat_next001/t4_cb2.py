# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0x637900 .. 0x637980 : the context that calls 0x637720 (0x637945) ===")
for l in pe.dis(0x6378E0, 55):
    print(l)
print()
print("=== 0x629320 (sender of message 0x27) full context: 0x6292F0..0x6293A0 ===")
for l in pe.dis(0x6292F0, 45):
    print(l)
