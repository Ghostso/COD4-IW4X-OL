# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_tools")
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
show(0x602430,0x602470,"0x602430 recv (no downstream)")
show(0x775A50,0x775A90,"0x775A50 recv (no downstream)")
show(0x775AB0,0x775B00,"0x775AB0 recvfrom (no downstream)")
show(0x6B4DE0,0x6B4E60,"0x6B4DE0 recvfrom head")
show(0x784F60,0x784FB0,"0x784F60 recv head")
open(r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_data\out_recv_bodies.txt","w",encoding="utf-8").write("\n".join(out))
print("\n".join(out))
