# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def dump(a,b,tag):
    print("="*72); print("%s  0x%X..0x%X"%(tag,a,b)); print("-"*72)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)], C.IB+a):
        r=ins.address-C.IB; mark=""
        if ins.mnemonic=="call":
            for op in ins.operands:
                if op.type==1: mark=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
        print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,mark))
    print()
dump(0xA2660,0xA2700,"body reader head")
dump(0xA2D40,0xA2E20,"body reader second MSG_ReadData @0xA2DC1")
dump(0xA2E20,0xA2E60,"body reader tail")
