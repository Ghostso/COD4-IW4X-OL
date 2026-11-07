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
    print("="*74); print(tag,"VA %08X RVA %06X"%(IB+rva,rva))
    o=off_of(rva)
    if o is None: print("NO_RAW"); return
    for ins in md.disasm(d[o:o+n],IB+rva):
        print("%06X %-22s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
for rva,name in [(0x685AD0,"0xA85AD0"),(0x685BE0,"0xA85BE0"),(0x685640,"0xA85640"),(0x687830,"0xA87830"),(0x6878A0,"0xA878A0")]:
    show(rva,0x60,name)
