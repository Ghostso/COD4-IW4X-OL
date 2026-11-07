# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

# symbolic esp tracking for the thread proc 0x23104F..0x231180
print("=== thread proc esp-relative annotation ===")
for i in dis_range(0x23109B, 0x231180):
    print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))

print()
print("=== object ctor call arg check: 0x23107C region ===")
for i in dis_range(0x231076, 0x2310F5):
    print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
