# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=C.off(0x3563C0)
for ins in md.disasm(C.d[o:o+0x120],C.IB+0x3563C0):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
print()
for va in (0xCB6B14,0xCB6B1C,0xCB6B28,0xCB5080,0xCB5088):
    b=C.bytes_rva(va-C.IB,48)
    print("  0x%X %r"%(va,b.split(b"\0")[0] if b else None))
