# -*- coding: utf-8 -*-
"""041 continued: look for a non-Winsock game transport (WKNet/kernel layer) in .text."""
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b

# 1) locate strings of interest across all sections
needles=[b"WKNet", b"wk_ip_config.ini", b"KernelBind", b"KernelConnect", b"KernelDisconnect",
         b"SendPacket", b"RecvPacket", b"DeviceIoControl", b"\\\\Device\\\\", b"\\\\\\\\.\\\\"]
found={}
for n in needles:
    st=0; hits=[]
    while True:
        j=b.find(n,st)
        if j<0: break
        r=C.off2rva(j)
        s=None
        if r is not None:
            # read surrounding cstring
            o=j
            while o>0 and 0x20<=b[o-1]<0x7f: o-=1
            e=b.find(b"\0",j)
            s=b[o:e].decode("latin1") if e>0 else ""
        hits.append((j,r,C.sec_of_rva(r) if r is not None else "?", s[:80]))
        st=j+1
    found[n.decode('latin1','replace')]=hits
    print("== %-18s hits=%d" % (n.decode('latin1','replace'), len(hits)))
    for j,r,s,t in hits[:12]:
        print("     off=0x%08X rva=%s sec=%s  ctx=%r" % (j, hex(r) if r else None, s, t))
