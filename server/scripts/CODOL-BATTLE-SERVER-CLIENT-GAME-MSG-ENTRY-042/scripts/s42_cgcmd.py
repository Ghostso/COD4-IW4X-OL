# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
CODE_LO,CODE_HI=0x1000,0x8a8000
code=b[CODE_LO:CODE_HI]
for s in (0x9c61ad,0x9c61dd,0x9c61a0,0x9c61c0,0x9c61f0,0x9b46c0,0x9b46e4,0x9bfc8c,0x9bff0c,0x9bfee8,0x9bfd04):
    va=C.IB+s; pat=struct.pack("<I",va); refs=[]; i=0
    while True:
        j=code.find(pat,i)
        if j<0: break
        refs.append(CODE_LO+j); i=j+1
    print("%08x refs=%s"%(s,[hex(x) for x in refs]))
