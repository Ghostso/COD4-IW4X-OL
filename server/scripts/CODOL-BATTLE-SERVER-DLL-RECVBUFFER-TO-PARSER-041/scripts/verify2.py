# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
# checksum helper reads eax as pointer; loop 6 x 8 bytes = 0x30 ; called with eax = this[+0xC]
print("call site of checksum 0x2360B0:")
for i in dis_range(0x235E9E, 0x235EB0):
    print("  0x%06X %-10s %s  [%s]" % (i.address-IB, i.mnemonic, i.op_str, i.bytes.hex()))
print()
print("sendto arg setup 0x235EB0..0x235ED0:")
for i in dis_range(0x235EB0, 0x235ED0):
    print("  0x%06X %-10s %s  [%s]" % (i.address-IB, i.mnemonic, i.op_str, i.bytes.hex()))
