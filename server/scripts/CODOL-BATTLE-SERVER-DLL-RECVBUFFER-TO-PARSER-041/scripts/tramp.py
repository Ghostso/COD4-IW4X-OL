# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b

print("=== obfuscated region 0x230F00..0x231050 disasm ===")
for i in dis_range(0x230F00, 0x231050):
    print("  0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))

print()
print("=== what is at 0x13517B2F, 0x135217A7, 0x13568B7B ===")
for r in [0x34F7E2F and 0, 0]:
    pass
for va in [0x13517B2F, 0x135217A7, 0x13568B7B]:
    rva = va - IB
    print("  0x%08X -> rva 0x%08X sec=%s" % (va, rva, sec_of_rva(rva)))
    for i in dis_n(rva, 12):
        print("      0x%06X %-10s %s" % (i.address-IB, i.mnemonic, i.op_str))
