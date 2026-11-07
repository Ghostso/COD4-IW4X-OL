# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
for name, lo, hi in [("consumer? 0x22E0A0",0x22E0A0,0x22E1A0),
                     ("consumer? 0x230A00",0x230A00,0x230B60)]:
    print("=== %s (0x%06X..0x%06X) ===" % (name,lo,hi))
    for i in dis_range(lo,hi):
        print("  0x%06X  %-12s %s" % (i.address-IB,i.mnemonic,i.op_str))
    print()
