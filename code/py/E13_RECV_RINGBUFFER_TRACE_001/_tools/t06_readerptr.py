# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
print("=== all refs to +0x89244 ===")
for ins in sweep(md,text,base):
    if "0x89244" in ins.op_str:
        print("   %06X %-22s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
print()
print("=== 0x352570 readable-length logic ===")
o2,_=C.off(0x352570)
for ins in md.disasm(C.d[o2:o2+0x80],C.IB+0x352570):
    print("   %06X %-22s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
