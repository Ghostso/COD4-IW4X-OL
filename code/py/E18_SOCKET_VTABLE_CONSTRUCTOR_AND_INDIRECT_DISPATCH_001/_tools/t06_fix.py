# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# VA 0xA84CE0 -> RVA 0x684CE0
def show(va,tag,n=0x90):
    rva=va-0x400000
    print("=== %s VA 0x%X (RVA 0x%X) ==="%(tag,va,rva))
    o,_=C.off(rva)
    for ins in md.disasm(C.d[o:o+n],C.IB+rva):
        r=ins.address-C.IB; m=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==1: m=" -> VA 0x%X"%(op.imm)
        print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
    print()
show(0xA84CE0,"delivery point")
show(0xA86220,"ctor helper")
