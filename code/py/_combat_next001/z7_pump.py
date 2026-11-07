# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def fs(va):
    for back in range(1, 0x1800):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

print("=== 0x7FA800 的 7 个调用点 ===")
for v in pe.calls_to(0x7FA800):
    f = fs(v)
    print("   %08X  (func ~%s)" % (v, hex(f) if f else "?"))

print()
print("=== 0x7FA450 (called at 0x7FA64E inside 0x7FA640) ===")
for l in pe.dis(0x7FA450, 45):
    print(l)
