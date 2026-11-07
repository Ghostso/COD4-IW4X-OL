# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *

print("=== fn containing CreateThread site: 0x22D470 .. 0x22D580 ===")
for i in dis_range(0x22D470, 0x22D580):
    print("0x%06X  %-12s %s" % (i.address-IB, i.mnemonic, i.op_str))

print()
# locate all dword refs to 0x1022D470
b = C._b
for va,label in [(0x1022D470,"thread-create-fn"),(0x1022D580,"helper"),(0x10231050,"thread-proc")]:
    pat = struct.pack("<I", va)
    hits=[]; st=0
    while True:
        j=b.find(pat,st)
        if j<0: break
        r=C.off2rva(j); hits.append((j,hex(r) if r else None,C.sec_of_rva(r) if r else "?")); st=j+1
    print("refs to", label, va, ":", hits)
