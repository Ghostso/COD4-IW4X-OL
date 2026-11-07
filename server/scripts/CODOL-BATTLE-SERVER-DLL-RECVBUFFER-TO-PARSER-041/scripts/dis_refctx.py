# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
print("=== around 0x22D534 (just before/after) ===")
for i in dis_range(0x22D4E0, 0x22D570):
    print("0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
print()
print("=== around 0x22FD7C ===")
for i in dis_range(0x22FD40, 0x22FDB0):
    print("0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
