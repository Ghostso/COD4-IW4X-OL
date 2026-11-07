import pefile, struct
from capstone import *
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
def rva2off(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
T=0xD9AB8AC
o=rva2off(T)
print("=== bytes at RVA 0x%X (file 0x%X) ===" % (T,o))
print(rec[o-16:o+48].hex(" "))
md=Cs(CS_ARCH_X86,CS_MODE_32)
print("=== disasm around it ===")
n=0
for ins in md.disasm(rec[o-16:o+64], IB+T-16):
    print("  %08X (RVA %X)  %-10s %s" % (ins.address, ins.address-IB, ins.mnemonic, ins.op_str)); n+=1
    if n>18: break
print()
print("=== distribution of .text rel32 targets into .tvm0 (top 15) ===")
import collections
tv,_,tr,ts=S[".text"]; text=rec[tr:tr+ts]
c=collections.Counter()
for i in range(len(text)-5):
    if text[i] in (0xE8,0xE9):
        disp=struct.unpack_from("<i",text,i+1)[0]
        dest=(tv+i+5+disp)
        if 0xD958000<=dest<0xDC11000: c[dest]+=1
for k,v in c.most_common(15): print("   RVA 0x%X : %d" % (k,v))
print("  distinct targets:",len(c), " total branches:",sum(c.values()))
print()
print("=== are those call sites 'call' or 'jmp'? and operand shape ===")
cnt={"E8":0,"E9":0}
for i in range(len(text)-5):
    if text[i] in (0xE8,0xE9):
        disp=struct.unpack_from("<i",text,i+1)[0]
        dest=(tv+i+5+disp)
        if 0xD958000<=dest<0xDC11000: cnt["E8" if text[i]==0xE8 else "E9"]+=1
print("  ",cnt)