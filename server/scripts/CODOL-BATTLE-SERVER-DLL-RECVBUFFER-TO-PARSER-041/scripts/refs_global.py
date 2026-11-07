# -*- coding: utf-8 -*-
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b

def refs_dword(va):
    pat=struct.pack("<I",va); hits=[]; st=0
    while True:
        j=b.find(pat,st)
        if j<0: break
        r=C.off2rva(j); hits.append((j,r,C.sec_of_rva(r) if r else "?")); st=j+1
    return hits

# map globals
for va,label in [(0x10AC4A08,"mutex1"),(0x10AC4A0C,"mutex2"),(0x10AC4A10,"map-sentinel?"),
                 (0x10AC4A28,"map-end?"),(0x10AC4A2C,"map-flag"),
                 (0x10AC49C0,"mutexA"),(0x10AC49D8,"mapA-end")]:
    H=refs_dword(va)
    print("%-14s 0x%08X refs=%d" % (label,va,len(H)))
    for j,r,s in H[:24]:
        print("     off=0x%08X rva=%s sec=%s" % (j,hex(r) if r else None,s))
