import sys, pefile, collections
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_tools")
from sweep import sweep
from capstone import *
from capstone.x86 import *
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
ttv,ttvs,ttr,ttrs=S[".text"]; tv,tvs,tr,trs=S[".tvm0"]
print("=== coverage check ===")
ins=0; last=ttv
for x in sweep(md, rec[ttr:ttr+ttrs], IB+ttv):
    ins+=1; last=x.address-IB
print("  .text resync sweep instructions=%d  last RVA=0x%X (section end 0x%X)" % (ins,last,ttv+ttrs))
ins2=0; last2=tv
for x in sweep(md, rec[tr:tr+trs], IB+tv):
    ins2+=1; last2=x.address-IB
print("  .tvm0 resync sweep instructions=%d  last RVA=0x%X (section end 0x%X)" % (ins2,last2,tv+tvs))
print()
# instruction boundaries in .text
bounds=set()
for x in sweep(md, rec[ttr:ttr+ttrs], IB+ttv): bounds.add(x.address-IB)
print("  .text instruction-boundary set size=%d" % len(bounds))
print()
print("=== PROPER+RESYNC: call targets into 0xA0000-0xAFFFF ===")
tgt=collections.Counter(); tot=0
for ins in sweep(md, rec[ttr:ttr+ttrs], IB+ttv):
    if ins.id==X86_INS_CALL:
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                rva=op.imm-IB
                if 0xA0000<=rva<0xB0000: tgt[rva]+=1; tot+=1
print("  calls into cluster: %d (distinct %d)" % (tot,len(tgt)))
for k,v in tgt.most_common(20): print("     RVA 0x%X : %d" % (k,v))
print()
print("=== PROPER+RESYNC: anything calling 0xA2E50 / 0xA2D90? ===")
for T in (0xA2E50,0xA2D90):
    c=0; sites=[]
    for ins in sweep(md, rec[ttr:ttr+ttrs], IB+ttv):
        if ins.id in (X86_INS_CALL,X86_INS_JMP):
            for op in ins.operands:
                if op.type==X86_OP_IMM and op.imm-IB==T: c+=1; sites.append(ins.address-IB)
    print("  0x%X : %d  %s" % (T,c,[hex(x) for x in sites[:6]]))
print()
print("=== PROPER+RESYNC: .text -> .tvm0 calls ===")
c=0; tt=collections.Counter()
for ins in sweep(md, rec[ttr:ttr+ttrs], IB+ttv):
    if ins.id in (X86_INS_CALL,X86_INS_JMP):
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                r=op.imm-IB
                if tv<=r<tv+tvs: c+=1; tt[r]+=1
print("  into .tvm0: %d (distinct %d)" % (c,len(tt)))
for k,v in tt.most_common(8): print("     RVA 0x%X : %d" % (k,v))