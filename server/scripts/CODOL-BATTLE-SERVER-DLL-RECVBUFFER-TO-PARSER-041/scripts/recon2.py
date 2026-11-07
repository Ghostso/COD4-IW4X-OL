# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
ins = dis_range(0x230FC0, 0x231180)
for i in ins:
    print("0x%06X  %-10s %s" % (i.address - IB, i.mnemonic, i.op_str))
