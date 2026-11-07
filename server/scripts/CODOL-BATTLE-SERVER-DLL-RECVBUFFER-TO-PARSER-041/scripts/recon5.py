# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
import _common as C

b = C._b
def fn_start(rva, maxback=0x4000):
    o = C.rva2off(rva)
    i = o - 1
    steps = 0
    while i > 0 and steps < maxback:
        if b[i] == 0xCC and b[i-1] == 0xCC:
            return C.off2rva(i+1)
        i -= 1; steps += 1
    return None

for r in [0x22D534, 0x22FD7C, 0x22A670, 0x22D580]:
    print("0x%06X -> fn_start 0x%06X" % (r, fn_start(r) or 0))

print()
# callers of these functions
calls = scan_call_rel32()
def callers_of(fr):
    va = IB + fr
    out = []
    for i in calls:
        if target_of(i) == va:
            out.append(i.address - IB)
    return out
for r in [0x22D534, 0x22FD7C, 0x22A670, 0x22D580]:
    fr = fn_start(r)
    print("callers of 0x%06X:" % fr, [hex(x) for x in callers_of(fr)])
