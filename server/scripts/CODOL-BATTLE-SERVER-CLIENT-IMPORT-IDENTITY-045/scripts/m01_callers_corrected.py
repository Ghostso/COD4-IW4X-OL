# -*- coding: utf-8 -*-
"""045: corrected caller/data-ref scan in the right address space.
   image file_offset == RVA; VA = 0x400000 + RVA.  "0x87BE00" is an RVA (VA 0xC7BE00)."""
import sys, struct
sys.stdout.reconfigure(encoding="utf-8")
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
b=open(IMG,"rb").read(); IB=0x400000
LO,HI=0x1000,0x8a7000
RVA_THUNK=0x87BA50; RVA_PRIM=0x87BE00
VA_THUNK=IB+RVA_THUNK; VA_PRIM=IB+RVA_PRIM
print("RVA_THUNK=%08X VA=%08X   RVA_PRIM=%08X VA=%08X"%(RVA_THUNK,VA_THUNK,RVA_PRIM,VA_PRIM))
print()
print("=== rel32 E8/E9 sites whose target VA == thunk or primitive ===")
hitsT=[]; hitsP=[]
for i in range(LO,HI-5):
    if b[i] in (0xE8,0xE9):
        rel=struct.unpack("<i",b[i+1:i+5])[0]
        tgt=IB+i+5+rel
        if tgt==VA_THUNK: hitsT.append((i,b[i]))
        if tgt==VA_PRIM: hitsP.append((i,b[i]))
print("  -> thunk   : %d site(s) %s"%(len(hitsT),["RVA %08X (%s)"%(a,"call" if o==0xE8 else "jmp") for a,o in hitsT]))
print("  -> primitiv: %d site(s) %s"%(len(hitsP),["RVA %08X (%s)"%(a,"call" if o==0xE8 else "jmp") for a,o in hitsP]))
print()
print("=== data dwords equal to VA thunk / primitive (jump tables, vtable) ===")
for lab,va in (("thunk",VA_THUNK),("primitive",VA_PRIM)):
    pat=struct.pack("<I",va); st=0; out=[]
    while True:
        j=b.find(pat,st)
        if j<0: break
        out.append(j); st=j+1
    print("  %s (VA %08X): %d data refs %s"%(lab,va,len(out),["RVA %08X"%x for x in out[:20]]))
print()
print("=== data dwords equal to RVA-as-absolute (0x0087BA50 / 0x0087BE00) — the mis-mapping check ===")
for lab,val in (("0x87BA50",0x87BA50),("0x87BE00",0x87BE00)):
    pat=struct.pack("<I",val); st=0; out=[]
    while True:
        j=b.find(pat,st)
        if j<0: break
        out.append(j); st=j+1
    print("  %s: %d refs %s"%(lab,len(out),["RVA %08X"%x for x in out[:20]]))
