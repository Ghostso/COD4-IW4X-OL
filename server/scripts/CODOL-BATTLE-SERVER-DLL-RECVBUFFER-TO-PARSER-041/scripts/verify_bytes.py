# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
print("=== raw bytes 0x235E00..0x2360B0 (key ranges) ===")
for lo,hi in [(0x235EF9,0x235EB0),(0x235E8D,0x235EB0),(0x235F52,0x235FD0),(0x236058,0x23607C)]:
    pass
for i in range(0, 0):
    pass
def dump(lo, hi, note):
    print("--- %s: 0x%06X..0x%06X ---" % (note, lo, hi))
    d = raw(lo, hi-lo)
    for k in range(0, len(d), 16):
        r = lo+k
        print("  0x%06X  %s" % (r, " ".join("%02x"%c for c in d[k:k+16])))
dump(0x235E84, 0x235EB0, "build ICMP echo request")
dump(0x235F94, 0x235FD0, "parse IP/ICMP header")
dump(0x236058, 0x23607C, "write out struct")
dump(0x2310D7, 0x2310F0, "caller: recv-body call")
dump(0x231145, 0x231190, "caller tail")
print()
print("=== exact disasm of 0x231050 prologue/tail ===")
for i in dis_range(0x231050, 0x231065):
    print("  0x%06X %-10s %s" % (i.address-IB, i.mnemonic, i.op_str))
print("  ...")
for i in dis_range(0x23115E, 0x231192):
    print("  0x%06X %-10s %s" % (i.address-IB, i.mnemonic, i.op_str))
