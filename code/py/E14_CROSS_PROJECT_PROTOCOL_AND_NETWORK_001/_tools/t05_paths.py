# -*- coding: utf-8 -*-
import sys,struct,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
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
show(0x6029A0,0x602A30,"0x6029A0 recv wrapper")
show(0x605220,0x6052E0,"0x605220 recv wrapper")
show(0x6104D0,0x610540,"0x6104D0")
show(0x672460,0x6724E0,"0x672460")
o2,_=C.off(0x898580)
raw=C.d[o2:o2+0x80]
out.append("### .rdata 0x898580..0x898600")
out.append(" ".join(hex(struct.unpack_from("<I",raw,i)[0]) for i in range(0,0x80,4)))
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_data\out_paths.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
