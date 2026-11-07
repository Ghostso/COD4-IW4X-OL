# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def cstr(va, maxn=140):
    b = pe.read(va, maxn)
    if not b: return None
    z = b.find(b"\0")
    return b[:z if z >= 0 else maxn].decode("latin1", "replace")

print("=== 0x6293B0 (called from accepted handler 0x63285A) ===")
for l in pe.dis(0x6293B0, 70):
    print(l)
print()
print("=== region around the call site 0x6294AF ===")
for l in pe.dis(0x629470, 40):
    print(l)
