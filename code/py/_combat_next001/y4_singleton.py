# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def fs(va):
    for back in range(1, 0x1500):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC: return x + 1
    return None

print("=== 0x639D1E : writer of [0x82E13FC] ===")
f = fs(0x639D1E)
print("   enclosing function = %s" % (hex(f) if f else "?"))
for l in pe.dis(0x639CFF, 50):
    print(l)
print()
print("=== callers of that function ===")
if f:
    for v in pe.calls_to(f):
        ff = fs(v)
        print("   %08X (in ~%s)" % (v, hex(ff) if ff else "?"))
print()
print("=== 0x629BAF / 0x629E3F / 0x632D8F callers ===")
for fn in (0x629BAF, 0x629E3F, 0x632D8F):
    c = pe.calls_to(fn)
    print("   0x%08X -> %d callers" % (fn, len(c)))
    for v in c[:8]:
        ff = fs(v)
        print("      %08X (in ~%s)" % (v, hex(ff) if ff else "?"))
