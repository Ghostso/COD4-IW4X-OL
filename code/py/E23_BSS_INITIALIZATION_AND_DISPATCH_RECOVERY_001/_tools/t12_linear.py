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
TV=[0xA85AD0,0xA85BE0,0xA85640,0xA87830,0xA878A0]
# linear disasm whole .text collecting true call targets
n,va,vs,rp,rs=[s for s in secs if s[0]==".text"][0]
data=d[rp:rp+rs]
counts={t:[] for t in TV}
for ins in md.disasm(data,IB+va):
    if ins.mnemonic=="call" and ins.operands and ins.operands[0].type==1:
        tgt=ins.operands[0].imm & 0xffffffff
        if tgt in counts:
            counts[tgt].append(ins.address-IB)
for t in TV:
    print("VA %08X true-call sites: %d"%(t,len(counts[t])))
    print("   ", [hex(x) for x in counts[t][:24]])
print()
# identify 0xb49b40
o=off_of(0x749B40)
print("== 0xB49B40 (0x749B40) ==")
for ins in md.disasm(d[o:o+0x60],IB+0x749B40):
    print("%06X %-18s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
print()
print("== 0xA878A0 tail (6878E3..) ==")
o=off_of(0x6878E3)
for ins in md.disasm(d[o:o+0x60],IB+0x6878E3):
    print("%06X %-18s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
