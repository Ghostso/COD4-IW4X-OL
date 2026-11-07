# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
regions=[(0x340000,0x360000,"0x34xxxx-0x35xxxx"),(0xA0000,0xA3000,"0xA0xxx-0xA2xxx"),(0x60000,0x70000,"0x6xxxx"),(0x1AC000,0x1B0000,"0x1ACxxx")]
print("=== cmp/sub/test with immediate 4 in key regions ===")
for ins in sweep(md,text,base):
    r=ins.address-C.IB
    for lo,hi,tag in regions:
        if lo<=r<hi:
            if ins.mnemonic in ("cmp","sub") and any(op.type==X86_OP_IMM and op.imm==4 for op in ins.operands):
                print("  [%s] 0x%06X  %s %s"%(tag,r,ins.mnemonic,ins.op_str))
            break
print()
print("=== push 4 in key regions (read-length markers) ===")
for ins in sweep(md,text,base):
    r=ins.address-C.IB
    for lo,hi,tag in regions:
        if lo<=r<hi:
            if ins.mnemonic=="push" and any(op.type==X86_OP_IMM and op.imm==4 for op in ins.operands):
                print("  [%s] 0x%06X  push 4"%(tag,r))
            break
