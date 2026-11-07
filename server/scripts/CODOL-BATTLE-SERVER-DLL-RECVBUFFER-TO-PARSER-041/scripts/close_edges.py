# -*- coding: utf-8 -*-
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b

def dword_refs_anysec(va):
    pat=struct.pack("<I",va); hits=[]; st=0
    while True:
        j=b.find(pat,st)
        if j<0: break
        r=C.off2rva(j); hits.append((r, C.sec_of_rva(r) if r else "?")); st=j+1
    return hits

for fr in [0x22A670,0x22A770,0x22AF90,0x22B010,0x22D580,0x22D910,0x22D990,0x22D470,0x22FD70]:
    H=dword_refs_anysec(IB+fr)
    secs=set(s for _,s in H)
    print("fn 0x%06X dword-ref (ptr tables) count=%d secs=%s" % (fr,len(H),sorted(secs)))
    for r,s in H[:8]:
        print("       rva=%s sec=%s" % (hex(r) if r else None, s))

print()
print("=== reads of [reg+0x14] in ping manager region 0x22A600..0x22E300 ===")
for i in dis_range(0x22A600, 0x22E300):
    if re.search(r"\+\s*0x14\]", i.op_str) and i.mnemonic.startswith("mov"):
        print("   0x%06X %-10s %s" % (i.address-IB,i.mnemonic,i.op_str))
