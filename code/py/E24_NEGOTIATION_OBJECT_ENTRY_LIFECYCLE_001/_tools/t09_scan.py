# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img(); IB=img.IB
# scan ALL raw sections' .text bytes for "cc 05 00 00" preceded by a mov (C7 /x) pattern
secs=img.secs
print("=== raw scan for disp32=0x5CC with mov-imm opcode C7 (any section with bytes) ===")
for nm,va,vs,rp,rs,x in secs:
    if rs==0: continue
    blob=img.d[rp:rp+rs]
    pat=b"\xcc\x05\x00\x00"
    i=0
    while True:
        j=blob.find(pat,i)
        if j<0: break
        start=va+j
        # check preceding bytes for C7 8x / C7 4x patterns within 8 bytes
        ctx=blob[max(0,j-6):j+10]
        print("  %-6s approx RVA %06X  ctx=%s"%(nm,start,ctx.hex()))
        i=j+1
print()
print("=== raw scan disp32=0x5F4 ===")
for nm,va,vs,rp,rs,x in secs:
    if rs==0: continue
    blob=img.d[rp:rp+rs]; pat=b"\xf4\x05\x00\x00"; i=0
    while True:
        j=blob.find(pat,i)
        if j<0: break
        print("  %-6s approx RVA %06X ctx=%s"%(nm,va+j,blob[max(0,j-5):j+9].hex()))
        i=j+1
