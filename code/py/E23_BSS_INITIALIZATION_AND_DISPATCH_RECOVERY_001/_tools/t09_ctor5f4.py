import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def off_of(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return rp+r-va if rs and r-va<rs else None
def sec(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return n
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def show(rva,n,tag):
    print("="*74); print(tag,"VA %08X RVA %06X sec=%s"%(IB+rva,rva,sec(rva)))
    o=off_of(rva)
    if o is None: print("NO_RAW"); return
    for ins in md.disasm(d[o:o+n],IB+rva):
        print("%06X %-20s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
# constructor of [edi+0x5f4] object
show(0x687BA0,0x90,"ctor 0xa87ba0")
print()
# check what section .tvm0 helpers are in
for rva in (0xDB9AA45-0x400000,0xDB4A028-0x400000,0xDB6216D-0x400000,0xDB6F97C-0x400000,0x74B40):
    pass
for va in (0xdf9aa45,0xdf4a028,0xdf6216d,0xdf6f97c,0xb49b40,0xb49b31,0xb7b800,0xb49b40):
    r=va-IB
    print("VA %08X -> RVA %06X sec=%s"%(va,r,sec(r)))
