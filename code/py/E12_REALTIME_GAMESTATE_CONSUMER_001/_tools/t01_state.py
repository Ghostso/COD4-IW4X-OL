# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
# find all instructions touching 0x1bbbcfc
print("=== instructions touching 0x1BBBCFC ===")
n=0
for ins in sweep(md,text,base):
    if "0x1bbbcfc" in ins.op_str:
        print("  %06X %-22s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str)); n+=1
print("total",n)
