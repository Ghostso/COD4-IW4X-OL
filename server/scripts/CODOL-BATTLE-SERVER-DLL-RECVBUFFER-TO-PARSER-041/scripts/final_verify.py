# -*- coding: utf-8 -*-
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
import pefile
b=C._b

def dword_refs(va):
    pat=struct.pack("<I",va); hits=[]; st=0
    while True:
        j=b.find(pat,st)
        if j<0: break
        r=C.off2rva(j); hits.append((j,r,C.sec_of_rva(r) if r else "?")); st=j+1
    return hits

targets=[0x10231050,0x10235CD0,0x10235E00,0x102360B0,0x10236110,0x1022D470,0x10235DC0]
for va in targets:
    H=dword_refs(va)
    print("dword-refs to VA 0x%08X : %d" % (va,len(H)))
    for j,r,s in H[:12]:
        print("    off=0x%08X rva=%s sec=%s" % (j,hex(r) if r else None,s))
print()
# socket-family FF15 uniqueness
def tgt15(ins):
    m=re.search(r"\[(0x[0-9a-f]+)\]",ins.op_str); return int(m.group(1),16) if m else None
ff=scan_ff15()
import collections
cnt=collections.Counter()
for i in ff: cnt[tgt15(i)]+=1
for va,label in [(0x10b02a60,"WSASocketW"),(0x10b02a48,"recvfrom#1"),(0x10b02b3c,"recvfrom#2"),
                 (0x10b02a4c,"sendto")]:
    print("%-14s slot 0x%08X ff15-callsites=%d" % (label,va,cnt.get(va,0)))
