# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== candidate #2: function 0x0050A52F (bulk copy into +0x160..) ===")
for l in pe.dis(0x50A52F, 70):
    print(l)
print()
print("=== what is at global 0x34A2820 ? ===")
print("   bytes: " + pe.read(0x34A2820, 64).hex(" ") if pe.read(0x34A2820, 64) else "   (not mapped)")
print()
print("=== callers of 0x50A52F ===")
for v in pe.calls_to(0x50A52F):
    print("   %08X" % v)
