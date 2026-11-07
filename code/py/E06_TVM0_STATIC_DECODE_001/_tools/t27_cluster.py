import pefile, struct, collections
from capstone import *
from capstone.x86 import *
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
ttv,ttvs,ttr,ttrs=S[".text"]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
text=rec[ttr:ttr+ttrs]
print("=== PROPER: instruction-level call targets into 0xA0000-0xAFFFF (message-parser cluster) ===")
tgt=collections.Counter(); total=0
for ins in md.disasm(text, IB+ttv):
    if ins.id==X86_INS_CALL:
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                rva=op.imm-IB
                if 0xA0000<=rva<0xB0000: tgt[rva]+=1; total+=1
print("  instruction-level calls into 0xA0000-0xAFFFF : %d (distinct %d)" % (total,len(tgt)))
for k,v in tgt.most_common(15): print("     RVA 0x%X : %d" % (k,v))
print()
print("  (compare: raw-byte scan claimed 1,458 -> over-count from bytes inside operands)")
print()
print("=== does anything call 0xA2E50 (proper instruction level, whole image)? ===")
for nm in (".text",".tvm0"):
    va,vs,rp,rs=S[nm]
    c=0
    for ins in md.disasm(rec[rp:rp+rs], IB+va):
        if ins.id in (X86_INS_CALL,X86_INS_JMP):
            for op in ins.operands:
                if op.type==X86_OP_IMM and op.imm==IB+0xA2E50: c+=1
    print("  %-7s -> 0xA2E50 : %d" % (nm,c))