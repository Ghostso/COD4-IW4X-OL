# -*- coding: utf-8 -*-
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
print("=== tail 0x231161 .. 0x2311F0 ===")
for i in dis_range(0x231161, 0x2311F0):
    print("0x%06X  %-12s %s" % (i.address - IB, i.mnemonic, i.op_str))
print()
# find callers of enclosing function start 0x231050
calls = scan_call_rel32()
jumps = scan_jmp_rel32()
tgt = IB + 0x231050
print("callers/jmpers of 0x10231050:")
for i in calls+jumps:
    t = target_of(i)
    if t == tgt:
        print("   0x%06X  %s %s" % (i.address-IB, i.mnemonic, i.op_str))
print()
# Also, what rel32 targets land in 0x2310xx range? (i.e. who calls into 0x231000-0x231200)
print("rel32 calls landing in 0x231000..0x231200:")
for i in calls:
    t = target_of(i)
    if t is not None and IB+0x231000 <= t < IB+0x231200:
        print("   0x%06X -> 0x%06X" % (i.address-IB, t-IB))
