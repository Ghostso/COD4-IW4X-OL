# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
def entry_below(off, back=0x2000):
    i=off
    while i>max(0x1000,off-back):
        if b[i-3:i]==b"\xcc\xcc\xcc":
            return i
        i-=1
    return None
def D(rva, end, label):
    print("=== %s RVA=%08x ===" % (label, rva))
    for i in C.dis_range(rva, end):
        print("  %08x  %-16s %-8s %s" % (i.address-C.IB, i.bytes.hex(), i.mnemonic, i.op_str))
e=entry_below(0x54b7b)
print("entry:", hex(e) if e else None)
if e: D(e, min(e+0x180,0x54c40), "gamestateupdate caller")
