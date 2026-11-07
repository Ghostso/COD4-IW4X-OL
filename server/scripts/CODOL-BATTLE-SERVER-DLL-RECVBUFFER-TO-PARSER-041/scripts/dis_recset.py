# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
for name, lo, hi in [("record setter 0x22B010",0x22B010,0x22B090),
                     ("record accessor 0x22A770",0x22A770,0x22A840)]:
    print("=== %s ===" % name)
    for i in dis_range(lo, hi):
        print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
    print()
