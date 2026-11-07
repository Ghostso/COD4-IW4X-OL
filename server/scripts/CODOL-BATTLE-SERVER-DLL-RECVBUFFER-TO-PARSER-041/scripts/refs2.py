# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b = C._b

def refs(va):
    pat = struct.pack("<I", va); hits=[]; st=0
    while True:
        j=b.find(pat,st)
        if j<0: break
        r=C.off2rva(j); hits.append((j,r,C.sec_of_rva(r) if r else "?")); st=j+1
    return hits

for rva,label in [(0x22D470,"thread-launch"),(0x22D580,"helper-0x22D580"),
                  (0x22FD70,"apc-start"),(0x22D910,"lock-helper"),
                  (0x22AF90,"map-lookup"),(0x231050,"thread-proc"),
                  (0x22D470+0x18,"?")]:
    va = IB+rva
    H = refs(va)
    print("refs to %-16s VA=0x%08X : %d" % (label, va, len(H)))
    for j,r,s in H[:12]:
        print("    off=0x%08X rva=%s sec=%s" % (j, hex(r) if r else None, s))
