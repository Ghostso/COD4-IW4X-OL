# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
def show(a,b,tag):
    out.append("="*74); out.append("%s  RVA 0x%X..0x%X"%(tag,a,b)); out.append("-"*74)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        r=ins.address-C.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
        out.append("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
show(0x6104D0,0x610590,"0x6104D0 full")
show(0x67F5A0,0x67F640,"0x67F5F0 call site")
show(0x5FB510,0x5FB5A0,"0x5FB510")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_data\out_6104d0.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
