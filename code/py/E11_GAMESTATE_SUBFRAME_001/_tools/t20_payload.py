# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
a,b=0x34FEB0,0x34FF40
o,_=C.off(a)
for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    out.append("  %06X %-24s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
print("\n".join(out))
