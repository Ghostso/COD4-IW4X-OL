# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
print("=== object ctor 0x235CD0..0x235E00 ===")
for i in dis_range(0x235CD0, 0x235E00):
    print("0x%06X  %-12s %s" % (i.address - IB, i.mnemonic, i.op_str))
