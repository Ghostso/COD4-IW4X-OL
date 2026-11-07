# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for a in (0x1B086D,0x1B0991,0x1B0A25,0x1B0ADF,0x1B0B44):
    print("=== 0x%06X ==="%a)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+0x28],C.IB+a):
        print("   %06X %-18s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
    print()
