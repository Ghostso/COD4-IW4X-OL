# -*- coding: utf-8 -*-
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

calls = scan_call_rel32()
jumps = scan_jmp_rel32()
by_target = collections.defaultdict(list)
for i in calls + jumps:
    t = target_of(i)
    if t is not None:
        by_target[t].append(i)

# who calls our function of interest (they are E8 targets)
def show(CALLERS, label):
    print("===", label, "===")
    for va in CALLERS:
        rva = va - IB
        ins = dis_at(rva)
        print("  0x%06X  %s" % (rva, ins))

# functions in 040 report
for f_rva, label in [(0x235CD0,"obj-ctor"), (0x235E00,"recv-body"), (0x2310E5,"caller-of-recv-body(0x2310E5)")]:
    print("\n#### target RVA 0x%06X (%s)" % (f_rva, label))
    # find rel32 calls into this function
    cs = by_target.get(IB+f_rva, [])
    print(" direct &-calls:", [hex(c.address-IB) for c in cs])

print("\n=== back-scan around 0x2310E5 size ===")
print("likely function start (padding scan):", hex(func_padding_before(0x2310E5) - IB))
