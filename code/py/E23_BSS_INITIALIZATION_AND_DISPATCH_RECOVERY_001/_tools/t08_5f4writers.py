import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def off_of(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return rp+r-va if rs and r-va<rs else None
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def show(rva,n,tag):
    print("="*72); print(tag,hex(IB+rva),"RVA",hex(rva))
    o=off_of(rva)
    for ins in md.disasm(d[o:o+n],IB+rva):
        print("%06X %-18s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
for rva,n,tag in [(0x6AA140,0x60,"0x6AA140 (5f4 refs)"),(0x6AA6C0,0x70,"0x6AA6C0 (5f4 ref)"),(0x6AB960,0x110,"0x6AB960 (5f4 refs)")]:
    show(rva,n,tag)
