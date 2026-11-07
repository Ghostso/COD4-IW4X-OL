# -*- coding: utf-8 -*-
"""045: raw E8/E9 rel32 scan into the 0x87Bxxx family + parse EXE export table."""
import sys, struct
sys.stdout.reconfigure(encoding="utf-8")
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
EXE=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
img=open(IMG,"rb").read(); exe=open(EXE,"rb").read(); IB=0x400000
LO,HI=0x1000,0x8a7000
def raw_scan():
    res={0x87BA50:[],0x87BE00:[]}
    for i in range(LO,HI-5):
        op=img[i]
        if op in (0xE8,0xE9):
            rel=struct.unpack("<i",img[i+1:i+5])[0]
            tgt=(IB+i)+5+rel
            if tgt in res: res[tgt].append((i,op))
    return res
print("=== raw E8/E9 rel32 sites targeting 0x87BA50 / 0x87BE00 ===")
for t,hits in raw_scan().items():
    print("  target %08X : %d sites %s"%(t,len(hits),["%08X(%s)"%(a,"call" if o==0xE8 else "jmp") for a,o in hits]))
print()
print("=== EXE export table ===")
# ExportDir RVA 0xA155B0 size 0x4C0 ; section#2 VA 0xa16000? no, 0xA155B0 is in section#1 (0x8a8000..0xa16000)
S1_VA,S1_RAW=0x8a8000,0x594000
def eo(rva): return S1_RAW+(rva-S1_VA)
exp_rva,exp_sz=0xA155B0,0x4C0
o=eo(exp_rva)
nfun,nnam=struct.unpack("<II",exe[o+0x14:o+0x1C])
addr_tbl,nam_tbl,ord_tbl=struct.unpack("<III",exe[o+0x1C:o+0x28])
print("  NumberOfFunctions=%d NumberOfNames=%d AddrOfFunctions=%08X AddrOfNames=%08X AddrOfNameOrd=%08X"%(nfun,nnam,addr_tbl,nam_tbl,ord_tbl))
names=[]
for k in range(nnam):
    nr=struct.unpack("<I",exe[eo(nam_tbl+4*k):eo(nam_tbl+4*k)+4])[0]
    off=eo(nr); e=exe.find(b"\x00",off)
    nm=exe[off:e].decode("latin1","replace")
    ordi=struct.unpack("<H",exe[eo(ord_tbl+2*k):eo(ord_tbl+2*k)+2])[0]
    fr=struct.unpack("<I",exe[eo(addr_tbl+4*ordi):eo(addr_tbl+4*ordi)+4])[0]
    names.append((ordi,nm,fr))
print("  %d named exports:"%len(names))
for ordi,nm,fr in names[:200]:
    print("    ord %3d  RVA %08X  %s"%(ordi,fr,nm))
