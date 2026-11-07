import pefile, struct
from capstone import *
from capstone.x86 import *
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(p,"rb").read()
pe=pefile.PE(p,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={}
for s in pe.sections:
    S[s.Name.rstrip(b"\x00").decode()]=(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData)
md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
targets={"0xA2E50(raw)":0x4A2E50, "0xA2E60(prologue)":0x4A2E60}
for label,T in targets.items():
    hits=[]
    for nm in (".text",".tvm0"):
        va,vs,rp,rs=S[nm]
        for ins in md.disasm(data[rp:rp+rs], IB+va):
            if ins.id in (X86_INS_CALL,X86_INS_JMP):
                for op in ins.operands:
                    if op.type==X86_OP_IMM and op.imm==T: hits.append((nm,ins.address))
    print("%-22s direct call/jmp = %d  %s" % (label, len(hits), ["0x%X"%h[1] for h in hits[:10]]))
# pointers to 0x4A2E60
for label,T in targets.items():
    pat=struct.pack("<I",T); c=0;o=0
    while True:
        i=data.find(pat,o)
        if i<0: break
        c+=1;o=i+1
    print("%-22s raw u32 pointer occurrences = %d" % (label,c))
# What text ranges ARE pointed to near 0x4A2E?? in .rdata
va,vs,rp,rs=S[".rdata"]; rdata=data[rp:rp+rs]
near=[]
for i in range(0,len(rdata)-4):
    v=struct.unpack_from("<I",rdata,i)[0]
    if 0x4A2000<=v<0x4A4000: near.append(v)
print("\n.rdata pointers landing in VA 0x4A2000..0x4A4000 :", len(near))
print("distinct:", sorted(set("0x%X"%x for x in near))[:30])