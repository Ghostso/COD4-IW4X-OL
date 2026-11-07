# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *

# Any reference to ebp-0x10C region i.e. lea ...,[ebp-0x10C] bytes 8d 8d f4 fe ff ff etc.
print("=== instructions referencing [ebp-0x10C] / [ebp-0x108] / [ebp-0x104] ===")
for i in dis_range(0x235E00, 0x2360B0):
    op=i.op_str
    if any(s in op for s in ["ebp - 0x10c","ebp - 0x108","ebp - 0x104","ebp - 0x10a","ebp - 0x120"]):
        print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, op))
