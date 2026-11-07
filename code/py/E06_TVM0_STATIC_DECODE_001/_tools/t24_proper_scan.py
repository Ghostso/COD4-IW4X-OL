import pefile, struct, collections
from capstone import *
from capstone.x86 import *
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
ttv,ttvs,ttr,ttrs=S[".text"]; tv,tvs,tr,trs=S[".tvm0"]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
text=rec[ttr:ttr+ttrs]
tgt=collections.Counter(); total_call=0; total_jmp=0; into=0
for ins in md.disasm(text, IB+ttv):
    if ins.id in (X86_INS_CALL, X86_INS_JMP):
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                if ins.id==X86_INS_CALL: total_call+=1
                else: total_jmp+=1
                dest=op.imm-IB
                if tv<=dest<tv+tvs: into+=1; tgt[dest]+=1
print("=== PROPER instruction-level scan of .text -> .tvm0 ===")
print("  total calls=%d  total jmps=%d  into .tvm0 = %d" % (total_call,total_jmp,into))
print("  distinct .tvm0 targets: %d" % len(tgt))
for k,v in tgt.most_common(20): print("     RVA 0x%X : %d" % (k,v))
print()
# how many are 'call' vs 'jmp' into tvm0
cc=0; jj=0
for ins in md.disasm(text, IB+ttv):
    if ins.id in (X86_INS_CALL,X86_INS_JMP):
        for op in ins.operands:
            if op.type==X86_OP_IMM and tv<=op.imm-IB<tv+tvs:
                if ins.id==X86_INS_CALL: cc+=1
                else: jj+=1
print("  into .tvm0: call=%d jmp=%d" % (cc,jj))
print()
print("=== disasm at 3 targets (proper) ===")
for T in [x for x,_ in tgt.most_common(3)]:
    o=None
    for nm,(v,vs,rp,rs) in S.items():
        if v<=T<v+min(vs,rs): o=rp+(T-v)
    print("--- RVA 0x%X ---" % T)
    n=0
    for ins in md.disasm(rec[o:o+48], IB+T):
        print("    %08X %-10s %s" % (ins.address,ins.mnemonic,ins.op_str)); n+=1
        if n>=10: break