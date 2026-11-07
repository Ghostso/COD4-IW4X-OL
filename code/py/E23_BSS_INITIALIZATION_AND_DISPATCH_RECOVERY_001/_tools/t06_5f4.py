import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def off_of(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return rp+r-va if rs and r-va<rs else None
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
t=[s for s in secs if s[0]==".text"][0]
n,va,vs,rp,rs=t
data=d[rp:rp+rs]
# disassemble whole .text and find instructions whose op_str mentions 0x5f4
hits=[]
for ins in md.disasm(data,IB+va):
    s=ins.op_str.lower()
    if "0x5f4" in s:
        hits.append((ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
print("total 0x5f4 refs:",len(hits))
for h in hits: print("%06X %-22s %s %s"%h)
