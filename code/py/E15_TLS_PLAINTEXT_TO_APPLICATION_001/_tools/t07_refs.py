# -*- coding: utf-8 -*-
import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
print("=== refs to VA 0xA72460 (0x672460) as immediate ===")
for ins in sweep(md,text,base):
    for op in ins.operands:
        if op.type==X86_OP_IMM and (op.imm & 0xffffffff)==0xA72460:
            print("   %06X %s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
print()
print("=== callers of 0x67F5F0-containing func: search nearby prologue ===")
# dump backward region to find function entry
for a in range(0x67F0,0x67F6,1):
    pass
o2,_=C.off(0x67F400)
for ins in md.disasm(C.d[o2:o2+0x220],C.IB+0x67F400):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
