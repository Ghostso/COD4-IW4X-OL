# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
out=[]
def show(a,b,tag):
    out.append("="*74); out.append("%s  0x%X..0x%X"%(tag,a,b)); out.append("-"*74)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        r=ins.address-C.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
        out.append("  %06X %-24s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    out.append("")
print("=== 4-item jump table @0x75025C ===")
o,_=C.off(0x35025C)
for i in range(4):
    v=struct.unpack_from("<I",C.d,o+i*4)[0]
    print("   value %d -> VA 0x%08X RVA 0x%06X"%(i+1,v,(v-C.IB)&0xffffffff))
print()
show(0x350170,0x350270,"0x350170 opcode dispatcher")
show(0x34FD80,0x350170,"0x34FD80 (opcode 2/3 handler)")
show(0x350040,0x350170,"0x350040 (opcode 1 handler)")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_data\out_top_dispatch.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
