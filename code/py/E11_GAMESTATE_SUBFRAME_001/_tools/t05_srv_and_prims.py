# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
def show(P,a,b,tag):
    out.append("="*74); out.append("%s  0x%X..0x%X"%(tag,a,b)); out.append("-"*74)
    o,_=P.off(a)
    for ins in md.disasm(P.d[o:o+(b-a)],P.IB+a):
        r=ins.address-P.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-P.IB)&0xffffffff)
        out.append("  %06X %-24s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
show(S,0xA0760,0xA0800,"SERVER 0xA0760..0xA0800 (before 0x04 write)")
show(S,0xA0960,0xA09C0,"SERVER 0xA0960..0xA09C0 (0x06 write)")
show(C,0x1AC670,0x1AC7B0,"CLIENT MSG_ReadBits 0x1AC670")
show(C,0x44C8C0,0x44C940,"CLIENT index-flag helper 0x44C8C0")
show(C,0x1ACB00,0x1ACB40,"CLIENT 0x1ACB00")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_data\out_srv_writer_and_prims.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
