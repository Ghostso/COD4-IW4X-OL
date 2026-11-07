import pefile, struct
from capstone import *
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
TV=0x0D958000; TE=TV+S[".tvm0"][1]
print(".tvm0 VA range 0x%08X..0x%08X (VSize 0x%X)" % (TV,TE,S[".tvm0"][1]))
print()
print("=== who REFERENCES .tvm0? ===")
# 1. .rdata pointers into .tvm0
rv,_,rr,rs=S[".rdata"]; rdata=rec[rr:rr+rs]
n=0; vals=[]
for i in range(0,len(rdata)-3,4):
    v=struct.unpack_from("<I",rdata,i)[0]
    if IB+TV<=v<IB+TE: n+=1; vals.append(v)
print("  .rdata 32-bit pointers into .tvm0: %d" % n)
for v in vals[:10]: print("     0x%08X" % v)
# 2. .text rel32 to .tvm0
tv,_,tr,ts=S[".text"]; text=rec[tr:tr+ts]
tgt=0; sites=[]
for i in range(len(text)-5):
    if text[i] in (0xE8,0xE9):
        disp=struct.unpack_from("<i",text,i+1)[0]
        dest=(IB+tv+i+5+disp)-IB
        if TV<=dest<TE: tgt+=1; sites.append((IB+tv+i,dest))
print("  .text rel32 branches into .tvm0: %d" % tgt)
for a,d in sites[:10]: print("     %08X -> RVA 0x%X" % (a,d))
# 3. absolute VA u32 anywhere pointing into .tvm0
c=0
for i in range(0,len(rec)-3,4):
    v=struct.unpack_from("<I",rec,i)[0]
    if IB+TV<=v<IB+TE: c+=1
print("  whole-image aligned u32 pointing into .tvm0: %d" % c)
print()
print("=== is depacked .tvm0 disassemblable as x86? ===")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
d=rec[S[".tvm0"][2]:S[".tvm0"][2]+0x10000]
tot=0; ok=0
for ins in md.disasm(d, IB+TV):
    tot+=1
    if tot>=20000: break
print("  instructions decoded (20KB window from start): %d" % tot)
# sanity: how many are 'in'/'out'/'int3'/invalid-ish opcodes