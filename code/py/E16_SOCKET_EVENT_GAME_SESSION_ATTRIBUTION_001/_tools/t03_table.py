# -*- coding: utf-8 -*-
import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
b=C.bytes_rva(0x7474EB0-0x400000,4)
print("count @0x7474EB0 =", struct.unpack("<I",b)[0] if b else None)
o,_=C.off(0x2CCA3C8)
for i in range(3):
    ent=C.d[o+i*0x80:o+i*0x80+0x80]
    print("  table[%d] %r"%(i,ent[:48].split(b"\0")[0]))
print()
o2,_=C.off(0x1B0860)
for ins in md.disasm(C.d[o2:o2+0x2A0],C.IB+0x1B0860):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
