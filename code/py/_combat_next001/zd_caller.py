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

print("=== caller function ~0x6379DF : full body ===")
print("   function start = %s" % (hex(fs(0x6379F4)) if fs(0x6379F4) else "?"))
f = fs(0x6379F4) or 0x6379DF
for l in pe.dis(f, 90):
    print(l)
