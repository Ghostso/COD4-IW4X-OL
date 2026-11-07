# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
print("all esp-relative accesses in thread proc 0x231050..0x23117F:")
for i in dis_range(0x231050, 0x23117F):
    if "esp +" in i.op_str or "esp -" in i.op_str:
        print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
print()
print("all esi accesses in thread proc after 0x231085:")
for i in dis_range(0x231085, 0x23117F):
    if "esi" in i.op_str:
        print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
