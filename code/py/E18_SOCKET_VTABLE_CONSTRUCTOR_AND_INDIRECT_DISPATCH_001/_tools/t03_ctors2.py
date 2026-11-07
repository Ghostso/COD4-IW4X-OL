# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
def show(a,b,tag):
    out.append("="*74); out.append("%s RVA 0x%X..0x%X"%(tag,a,b)); out.append("-"*74)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        r=ins.address-C.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
        out.append("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
show(0x776130,0x7761E0,"ctor near 0x776139/0x776188")
show(0x7763A0,0x7763E0,"0x7763A6 ctor")
show(0x7767C0,0x776810,"0x7767D2 ctor")
show(0x776B50,0x776C40,"0x776B64/0x776BE6/0x776C1A ctors")
show(0x776F00,0x776F40,"0x776F15 ctor")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_data\out_ctors.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
