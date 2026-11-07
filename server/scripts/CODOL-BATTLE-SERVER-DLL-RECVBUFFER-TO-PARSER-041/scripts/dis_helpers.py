# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *

print("=== checksum helper 0x2360B0 ===")
for i in dis_range(0x2360B0, 0x236110):
    print("0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
print()
print("=== 0x236110 (tick helper) ===")
for i in dis_range(0x236110, 0x236160):
    print("0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
print()
print("=== 0x22A670 ([esi+0x14] lookup) ===")
for i in dis_range(0x22A670, 0x22A730):
    print("0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
