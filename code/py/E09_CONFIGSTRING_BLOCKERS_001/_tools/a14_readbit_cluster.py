import sys, collections
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=C.off(0x1000); text=C.d[o:o+C.pe.sections[0].SizeOfRawData]
# collect ALL callers of BIT reader and BYTE reader and WRITEbits
RB=0x1AC670; RD=0x1AC1D0; WB=0x1AC2B0
sel={RB:[],RD:[],WB:[]}
for ins in sweep(md, text, C.IB+0x1000):
    if ins.id in (X86_INS_CALL,X86_INS_JMP):
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                r=op.imm-C.IB
                if r in sel: sel[r].append(ins.address-C.IB)
print("=== MSG_ReadBits (0x1AC670) callers inside the parser cluster 0xA0000-0xAFFFF ===")
for a in sorted(x for x in sel[RB] if 0xA0000<=x<0xB0000):
    print("   call site RVA 0x%X" % a)
print()
print("=== distribution of MSG_ReadBits callers by 64KB bucket ===")
c=collections.Counter(a>>16 for a in sel[RB])
for k,v in sorted(c.items()): print("   RVA 0x%X0000-0x%XFFFF : %d" % (k,k,v))