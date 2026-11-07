# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
def entry_below(off, back=0x600):
    b=C._b; i=off
    while i>max(0x1000,off-back):
        if b[i-3:i]==b"\xcc\xcc\xcc" and (b[i:i+2]==b"\x55\x8b" or b[i] in (0x83,0x81,0x6a,0x51,0xb8)):
            return i
        i-=1
    return None
def D(rva, end, label):
    print("=== %s RVA=%08x ===" % (label, rva))
    for i in C.dis_range(rva, end):
        print("  %08x  %-16s %-8s %s" % (i.address-C.IB, i.bytes.hex(), i.mnemonic, i.op_str))
for ref,lab in ((0x73214,"gamestateupdate ref #2 (0x73214)"),(0x731e1,"ConfigStringMismatch ref (0x731e1)"),
                (0x54b7b,"gamestateupdate ref #1 (0x54b7b)"),(0x778d7,"ExpectedNetConfigStringMismatch ref")):
    e=entry_below(ref)
    print("### %s : entry=%s" % (lab, hex(e) if e else None))
    if e: D(e, e+0x70, lab)
    print()
