# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
print("netevents struct base check + WSAEnumNetworkEvents usage:")
for i in dis_range(0x235F3F, 0x235F60):
    print("  0x%06X %-12s %s  [%s]" % (i.address-IB,i.mnemonic,i.op_str,i.bytes.hex()))
print()
print("checksum region recompute: 6 iterations x 8 bytes = 0x30 (matches sendto len)")
for i in dis_range(0x2360BF, 0x236106):
    print("  0x%06X %-12s %s" % (i.address-IB,i.mnemonic,i.op_str))
