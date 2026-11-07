# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def cstr(va, maxn=120):
    b = pe.read(va, maxn)
    if not b: return None
    z = b.find(b"\0")
    return b[:z if z >= 0 else maxn].decode("latin1", "replace")

print("=== strings at 0xDC6724 / 0xDC672C used by the 0x62F7EA call ===")
for va in (0xDC6724, 0xDC672C, 0xDC6730, 0xDC6740, 0xDC6750):
    print("   %08X %r" % (va, cstr(va)))
print()
print("=== full mmbook builder function 0x62F6F0 (tail: format + send) ===")
for l in pe.dis(0x62F7E0, 45):
    print(l)
print()
print("=== enclosing function of 0x62F6F0 boundary check ===")
for back in range(1, 0x600):
    va = 0x62F6F0 - back
    b = pe.read(va, 2)
    if b and b[0] == 0xCC and b[1] == 0xCC:
        print("   prev padding ends %08X -> func at %08X" % (va, va + 1)); break
