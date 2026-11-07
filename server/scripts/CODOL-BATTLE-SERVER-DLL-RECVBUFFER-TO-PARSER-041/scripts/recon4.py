# -*- coding: utf-8 -*-
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

# resolve a few IAT slots
def slot_name(va):
    v = rd32(va - IB)
    if v is None: return "?"
    if v & 0x80000000: return "ordinal:%d" % (v & 0xffff)
    hn = read_hintname(v)
    return hn[1].decode("latin1") if hn else "?"

for a in [0x10b0232c, 0x10b021c8, 0x10b0227c, 0x10b02400, 0x10b022d4, 0x10b02a9c, 0x10b02a40, 0x10ac4a0c]:
    print("0x%08X -> %s" % (a, slot_name(a)))

print()
print("=== find fn start containing 0x22D534 (back-scan int3) ===")
def fn_start(rva):
    o = rva2off(rva)
    i = o-1
    while i > 0:
        if _b[i] == 0xCC and _b[i-1] == 0xCC:
            return off2rva(i+1)
        i -= 1
    return None
print("start:", hex(fn_start(0x22D534)) if fn_start(0x22D534) else None)
