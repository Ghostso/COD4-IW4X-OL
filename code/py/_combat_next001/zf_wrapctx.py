# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def fs(va):
    for back in range(1, 0x1500):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

print("=== context of 0x62DE9C (single ref to wrapper 0x6379E0) ===")
print("   enclosing func ~%s" % (hex(fs(0x62DE9C)) if fs(0x62DE9C) else "?"))
for l in pe.dis(0x62DE50, 70):
    print(l)
