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

print("=== 0x7F1500 .. 0x7F15C0 (the mmbook string handler) ===")
for l in pe.dis(0x7F1500, 80):
    print(l)
print()
print("=== enclosing function of 0x7F153F ===")
for back in range(1, 0x1200):
    va = 0x7F153F - back
    b = pe.read(va, 2)
    if b and b[0] == 0xCC and b[1] == 0xCC:
        print("   ~%08X" % (va + 1)); break
print()
print("=== callers of that enclosing function region ===")
for t in (0x7F1400,):
    cc = pe.calls_to(t)
    print("   callers of %08X = %d" % (t, len(cc)))
    for v in cc[:12]:
        print("      %08X" % v)
