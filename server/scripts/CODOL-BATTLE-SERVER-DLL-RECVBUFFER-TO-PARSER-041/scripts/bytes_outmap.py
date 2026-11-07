# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
for lo,hi,note in [(0x2310D7,0x2310F8,"call+dispatch"),
                   (0x23115E,0x231181,"tail / out-field writeback"),
                   (0x23107C,0x2310AD,"prologue: D and out slots"),
                   (0x235F94,0x235FD5,"IP/ICMP header parse"),
                   (0x236058,0x23607C,"out struct writes")]:
    print("--- %s  0x%06X..0x%06X ---" % (note, lo, hi))
    d=raw(lo,hi-lo)
    for k in range(0,len(d),16):
        r=lo+k
        print("   0x%06X  %s" % (r," ".join("%02x"%c for c in d[k:k+16])))
    for i in dis_range(lo,hi):
        print("      0x%06X %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))
    print()
