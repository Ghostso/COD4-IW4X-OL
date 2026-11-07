# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
def show(a,b,tag):
    out.append("="*74); out.append("%s  0x%X..0x%X"%(tag,a,b)); out.append("-"*74)
    o,_=S.off(a)
    for ins in md.disasm(S.d[o:o+(b-a)],S.IB+a):
        r=ins.address-S.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-S.IB)&0xffffffff)
        out.append("  %06X %-24s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
show(0x179480,0x179560,"server 0x1794FE WriteByte(4) context")
show(0xA8680,0xA8730,"server 0xA86EC WriteByte(2) context")
show(0xA8580,0xA8660,"server 0xA85B7/0xA8639 WriteByte(3)/(5) context")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_data\out_srv_other_opcodes.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
