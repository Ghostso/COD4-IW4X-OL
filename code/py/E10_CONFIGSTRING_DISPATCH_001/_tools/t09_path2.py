# -*- coding: utf-8 -*-
import sys,pickle,bisect,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fstart(r):
    i=bisect.bisect_right(prologues,r)-1; return prologues[i] if i>=0 else None
def callsites(t):
    return sorted(set((s,k) for s,k,tg in edges if tg==t))
# Disassemble full 0x352E80 window including tail jumps
print("="*72); print("FULL 0x352E80..0x3530E0"); print("-"*72)
o,_=C.off(0x352E80)
for ins in md.disasm(C.d[o:o+(0x3530E0-0x352E80)],C.IB+0x352E80):
    r=ins.address-C.IB; mark=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==X86_OP_IMM: mark=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,mark))
print()
# who calls 0x352E80's callers
for f in (0x69C40,0x69CE0,0x34E7C0,0x5E350):
    print("callers of 0x%X:"%f)
    for s,k in callsites(f): print("   0x%X %s in 0x%X"%(s,k,fstart(s)))
