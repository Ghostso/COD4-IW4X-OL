# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def pushes(P,a,b,tag):
    print("=== %s ==="%tag)
    o,_=P.off(a)
    for ins in md.disasm(P.d[o:o+(b-a)],P.IB+a):
        if ins.mnemonic=="push":
            print("   %06X %s"%(ins.address-P.IB,ins.op_str))
pushes(C,0xA2480,0xA24B0,"CLIENT 0xA2480 first pushes")
pushes(C,0xA26E0,0xA2780,"CLIENT 0xA2660 pushes A1/A2")
pushes(S,0xA0880,0xA08F0,"SERVER 0xA0880 region")
