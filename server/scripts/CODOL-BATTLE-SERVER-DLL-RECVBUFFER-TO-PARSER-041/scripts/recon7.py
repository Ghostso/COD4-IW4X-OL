# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b

# Global scan: any E8/E9 rel32 anywhere that lands exactly on 0x1022D470
def global_rel_landings(target_va):
    hits=[]
    for i in range(0, len(b)-5):
        if b[i] in (0xE8,0xE9):
            src = C.off2rva(i)
            if src is None: continue
            rel = struct.unpack("<i", b[i+1:i+5])[0]
            if (IB+src+5+rel) == target_va:
                hits.append((src, b[i]))
    return hits
for va,lab in [(0x1022D470,"thread-launcher"),(0x10231050,"thread-proc"),(0x10235E00,"recv-body")]:
    print(lab, hex(va), "global rel landings:", [(hex(s),hex(op)) for s,op in global_rel_landings(va)][:10])
print()
print("=== 0x5303F0..0x530420 (jmp to 0x235DC0) ===")
for i in dis_range(0x5303F0, 0x530420):
    print("  0x%06X %-10s %s [%s]" % (i.address-IB,i.mnemonic,i.op_str,i.bytes.hex()))
print()
print("=== destructor 0x235DC0 ===")
for i in dis_range(0x235DC0, 0x235E00):
    print("  0x%06X %-10s %s" % (i.address-IB,i.mnemonic,i.op_str))
