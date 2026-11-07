# -*- coding: utf-8 -*-
import sys, os, struct, collections, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *

calls = scan_call_rel32()
by = collections.defaultdict(list)
for i in calls:
    t=target_of(i)
    if t is not None: by[t].append(i.address-IB)

def callers(fr): return by.get(IB+fr, [])

for fr,lab in [(0x22D470,"thread-launcher"),(0x22D610,"?"),(0x22B010,"record-map-setter"),
               (0x22A770,"record-lookup-ptr"),(0x22A670,"record-lookup-bykey"),
               (0x22AF90,"record-lowerbound"),(0x22D580,"map-getorcreate"),
               (0x22D910,"map-lowerbound"),(0x22D990,"map-insert"),
               (0x22A670,"key-lookup")]:
    cs=callers(fr)
    print("%-22s 0x%06X callers: %s" % (lab,fr,[hex(x) for x in cs][:12]))

# Also: what data feeds the ping-object key [esi+0x14]? find writes to +0x14 near ping objects
print()
print("=== map-setter (0x22B010) callers detail ===")
for a in by.get(IB+0x22B010, []):
    print("  caller 0x%06X:" % a)
    for i in dis_range(a-24, a+8):
        print("     0x%06X %-10s %s" % (i.address-IB,i.mnemonic,i.op_str))
