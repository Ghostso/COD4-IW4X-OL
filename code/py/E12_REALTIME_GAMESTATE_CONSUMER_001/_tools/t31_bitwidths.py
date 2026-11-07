# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== SERVER WriteBits calls inside 0xA0468..0xA0997 (bit widths) ===")
o,_=S.off(0xA0468)
for ins in md.disasm(S.d[o:o+(0xA0997-0xA0468)],S.IB+0xA0468):
    if ins.mnemonic=="push":
        for op in ins.operands:
            if op.type==1 and op.imm in (1,4,7,10,11,12,13,14):
                print("   %06X push %d"%(ins.address-S.IB,op.imm))
    if ins.mnemonic=="call":
        for op in ins.operands:
            if op.type==1 and (op.imm-S.IB)&0xffffffff==0x99590:
                print("   %06X call WriteBits"%(ins.address-S.IB))
print()
print("=== CLIENT 0xA2660 + 0xA2480 bit widths ===")
for a,b,tag in [(0xA2660,0xA2976,"0xA2660"),(0xA2480,0xA25F0,"0xA2480")]:
    print("--- %s ---"%tag)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        if ins.mnemonic=="push":
            for op in ins.operands:
                if op.type==1 and op.imm in (1,4,7,10,11,12,13,14):
                    print("   %06X push %d"%(ins.address-C.IB,op.imm))
