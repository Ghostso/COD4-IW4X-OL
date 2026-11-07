import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def off_of(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return rp+r-va if rs and r-va<rs else None
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001\_data\out_dispatch_full.txt","w",encoding="utf-8")
def show(rva,n,tag):
    OUT.write("="*74+"\n"+tag+" VA %08X RVA %06X\n"%(IB+rva,rva))
    o=off_of(rva)
    if o is None: OUT.write("NO_RAW\n"); return
    for ins in md.disasm(d[o:o+n],IB+rva):
        OUT.write("%06X %-22s %s %s\n"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
show(0x6AC0C0,0x310,"0x6AC0C0 full")
show(0x6AAE70,0x320,"0x6AAE70 full")
OUT.close()
print("written")
