# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
print("=== recv function 0x235E00 .. 0x23620x ===")
for i in dis_range(0x235E00, 0x2360C0):
    print("0x%06X  %-12s %s" % (i.address - IB, i.mnemonic, i.op_str))
