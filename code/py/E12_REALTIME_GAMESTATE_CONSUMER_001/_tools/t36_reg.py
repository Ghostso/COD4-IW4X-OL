# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
for a,b,tag in [(0x34DF80,0x34E100,"0x34DF80 registration function head"),(0x34E1A0,0x34E2A0,"0x34DF80 tail registrations")]:
    out.append("="*72); out.append("%s 0x%X..0x%X"%(tag,a,b)); out.append("-"*72)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        r=ins.address-C.IB; m=""
        if ins.mnemonic=="call":
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
        out.append("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_data\out_34df80_reg.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
