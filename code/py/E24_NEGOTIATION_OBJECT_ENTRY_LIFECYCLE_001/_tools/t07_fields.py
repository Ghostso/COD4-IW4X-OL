# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def refs(disp):
    """find instructions whose op_str mentions disp (like 0x5cc)"""
    hits=[]
    for ins in img.md.disasm(data, IB+va):
        s=ins.op_str.lower()
        if ("0x%x"%disp) in s or ("+ 0x%x"%disp) in s:
            hits.append((ins.address-IB, ins.mnemonic, ins.op_str))
    return hits
for d in (0x5cc,0x5d0,0x5d8,0x5e0,0x5e8,0x5f0,0x5f4,0x620,0x624,0xac,0xb0,0xc8,0x9c):
    h=refs(d)
    wr=[x for x in h if x[1]=="mov" and any(t.startswith(x[0] and "") for t in []) ]
    print("== disp 0x%x : %d refs =="%(d,len(h)))
    for r in h[:24]:
        print("   %06X %-6s %s"%r)
