# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
for name, lo, hi in [("map-helper 0x22D580",0x22D580,0x22D620),
                     ("lookup-helper 0x22D910",0x22D910,0x22D9C0),
                     ("record-lookup 0x22AF90",0x22AF90,0x22B020)]:
    print("=== %s ===" % name)
    for i in dis_range(lo, hi):
        print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
    print()
