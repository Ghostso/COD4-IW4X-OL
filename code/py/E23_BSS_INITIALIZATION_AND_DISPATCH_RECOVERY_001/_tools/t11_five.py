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
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001\_data\out_five_full.txt","w",encoding="utf-8")
def show(rva,n,tag):
    OUT.write("="*74+"\n"+tag+" VA %08X RVA %06X sec=%s\n"%(IB+rva,rva,sec(rva)))
    o=off_of(rva)
    if o is None: OUT.write("NO_RAW\n"); return
    for ins in md.disasm(d[o:o+n],IB+rva):
        OUT.write("%06X %-22s %s %s\n"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
show(0x685AD0,0x32,"TARGET 0xA85AD0")
show(0x685BE0,0x49,"TARGET 0xA85BE0")
show(0x685640,0x57,"TARGET 0xA85640")
show(0x687830,0x70,"TARGET 0xA87830")
show(0x6878A0,0x140,"TARGET 0xA878A0")
show(0x687D50,0x90,"VT 0xC5A31C slot+0xC = 0xA87D50")
OUT.close(); print("written")
