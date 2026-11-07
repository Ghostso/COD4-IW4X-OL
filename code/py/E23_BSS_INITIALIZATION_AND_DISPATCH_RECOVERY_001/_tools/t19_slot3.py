import pefile, struct
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
def off(r):
    for s in pe.sections:
        if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize:
            return s.PointerToRawData+r-s.VirtualAddress if s.SizeOfRawData and r-s.VirtualAddress<s.SizeOfRawData else None
def sec(r):
    for s in pe.sections:
        if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize: return s.Name.rstrip(b"\0").decode()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for rva in (0x6CE180,0x6CE1B0,0x6CE010):
    o=off(rva)
    print("="*60); print("RVA %06X sec=%s"%(rva,sec(rva)))
    if o is None: print(" NO_RAW"); continue
    for ins in md.disasm(d[o:o+0x40],IB+rva):
        print("  %06X %-18s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
# find function start containing 0x6AB9D8
print("\n== backwards 0xCC scan from 0x6AB9D8 ==")
r=0x6AB9D8
o=off(r)- (r-0x6AB000)
j=0x6AB9D8
while j>0x6AB000:
    if d[off(j)-1]==0xcc: break
    j-=1
print("candidate start:",hex(j))
o=off(j)
n=0
for ins in md.disasm(d[o:o+0x200],IB+j):
    print("  %06X %-18s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
    n+=1
    if n>70: break
