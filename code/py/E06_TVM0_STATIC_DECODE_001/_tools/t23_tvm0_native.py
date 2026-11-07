import pefile, struct
from capstone import *
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
tv,tvs,tr,trs=S[".tvm0"]
md=Cs(CS_ARCH_X86,CS_MODE_32)
# linear disassembly coverage over the whole .tvm0
seg=rec[tr:tr+tvs]
bounds=set(); off=0
insn=0
for ins in md.disasm(seg, IB+tv):
    bounds.add(ins.address-IB); insn+=1
print("=== .tvm0 linear disassembly ===")
print("  bytes=0x%X  instructions decoded=%d  coverage=%.2f%%" % (tvs,insn,100.0*insn/ (tvs/3.2) if tvs else 0))
print("  (max possible ~ bytes/1 byte each; report raw count)")
print("  last decoded RVA: 0x%X (section spans 0x%X..0x%X)" % (max(bounds) if bounds else 0, tv, tv+tvs))
print()
# collect .text targets into .tvm0
ttv,ttvs,ttr,ttrs=S[".text"]; text=rec[ttr:ttr+ttvs]
tg=[]
for i in range(len(text)-5):
    if text[i] in (0xE8,0xE9):
        disp=struct.unpack_from("<i",text,i+1)[0]
        dest=ttv+i+5+disp
        if tv<=dest<tv+tvs: tg.append(dest)
onb=sum(1 for t in tg if t in bounds)
print("=== are .text->.tvm0 targets aligned to instruction boundaries? ===")
print("  total targets=%d  aligned=%d (%.2f%%)" % (len(tg),onb,100.0*onb/max(1,len(tg))))
print()
# linear from the top-referenced target to see if it's real code
for T in (0xD9AB8AC,0xDB9AA45,0xDADEC1D):
    o=None
    for nm,(v,vs,rp,rs) in S.items():
        if v<=T<v+min(vs,rs): o=rp+(T-v)
    print("=== disasm at top target RVA 0x%X ===" % T)
    n=0
    for ins in md.disasm(rec[o:o+64], IB+T):
        print("   %08X %-10s %s" % (ins.address,ins.mnemonic,ins.op_str)); n+=1
        if n>=12: break