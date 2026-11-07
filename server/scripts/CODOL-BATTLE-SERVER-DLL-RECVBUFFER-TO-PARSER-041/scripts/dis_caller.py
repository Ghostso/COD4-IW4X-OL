# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
print("=== caller function 0x23104F .. 0x23115E ===")
for i in dis_range(0x23104F, 0x23115E):
    print("0x%06X  %-12s %s" % (i.address - IB, i.mnemonic, i.op_str))
print()
print("=== 0x104530EE / 0x10453124 / 0x1045313C / 0x1022A670 ===")
for r in [0x4530EE, 0x453124, 0x45313C, 0x22A670, 0x27D8F5, 0x28D28B if False else 0x27D28B]:
    print("---- 0x%06X ----" % r)
    for i in dis_n(r, 24):
        print("  0x%06X %-10s %s" % (i.address-IB, i.mnemonic, i.op_str))
