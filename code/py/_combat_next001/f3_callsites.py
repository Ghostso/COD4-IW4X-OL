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

for site in (0x5BEAEA, 0x5C2AB9):
    print("=" * 70)
    print("=== call site %08X (context before/after) ===" % site)
    for l in pe.dis(site - 0x60, 40):
        print(l)
    print()
