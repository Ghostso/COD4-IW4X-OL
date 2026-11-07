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

print("=== 0x7FB240 (called at 0x62DE82 with push 0x26) ===")
for l in pe.dis(0x7FB240, 50):
    print(l)
print()
print("=== callers of 0x7FB240 ===")
c = pe.calls_to(0x7FB240)
print("   count = %d" % len(c))
for v in c[:25]:
    print("      %08X (in ~%s)" % (v, hex(fs(v)) if fs(v) else "?"))
