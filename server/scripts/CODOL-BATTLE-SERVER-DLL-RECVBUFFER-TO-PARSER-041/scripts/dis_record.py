# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
for name, lo, hi in [("record-map find 0x22AF90",0x22AF90,0x22B020),
                     ("record init 0x22A71E",0x22A71E,0x22A7B0)]:
    print("=== %s ===" % name)
    for i in dis_range(lo, hi):
        print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
    print()
