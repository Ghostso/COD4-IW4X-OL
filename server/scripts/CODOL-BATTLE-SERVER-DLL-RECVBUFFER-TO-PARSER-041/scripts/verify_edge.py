# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
print("=== .tvm0 edge 0x3512437 (site that rel32-calls 0x1022D470) ===")
for i in dis_range(0x3512410, 0x3512460):
    print("  0x%06X [%s] %-10s %s" % (i.address-IB, sec_of_rva(i.address-IB), i.mnemonic, i.op_str))
print()
print("section of 0x3512437:", sec_of_rva(0x3512437))
print()
print("=== .tls ref site 0x17CCB37 (dword 0x10235E00) ===")
d = raw(0x17CCB20, 0x40)
for k in range(0,len(d),16):
    print("  0x%06X  %s" % (0x17CCB20+k, " ".join("%02x"%c for c in d[k:k+16])))
