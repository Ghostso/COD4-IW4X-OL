import sys, collections
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=C.off(0x1000); text=C.d[o:o+C.pe.sections[0].SizeOfRawData]
TARGETS={0x1AC670:"MSG_ReadBits",0x1AC1D0:"MSG_ReadData",0x1AC2B0:"MSG_WriteBits",0x1ACBB0:"?",0x1ACB00:"?"}
callers=collections.defaultdict(list)
for ins in sweep(md, text, C.IB+0x1000):
    if ins.id in (X86_INS_CALL,X86_INS_JMP):
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                r=op.imm-C.IB
                if r in TARGETS: callers[r].append(ins.address-C.IB)
for r,name in sorted(TARGETS.items()):
    cs=sorted(callers.get(r,[]))
    print("=== 0x%X (%s): %d callers ===" % (r,name,len(cs)))
    if cs:
        print("   first 30:", ["0x%X"%x for x in cs[:30]])
        print("   min=0x%X max=0x%X" % (min(cs),max(cs)))
    print()