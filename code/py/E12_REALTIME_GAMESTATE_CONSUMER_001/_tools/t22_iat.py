# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
targets={0xBAE50C:"recvfrom",0xBAE490:"recv",0xBAE504:"sendto",0xBAE4C8:"send",0xBAE22C:"ReadFile",0xBAE1E4:"CreateFileA"}
hits={k:[] for k in targets}
for ins in sweep(md,text,base):
    for op in ins.operands:
        if op.type==X86_OP_MEM:
            # disp is absolute VA for [0xBAE50C] style
            if op.mem.disp in targets:
                hits[op.mem.disp].append((ins.address-C.IB,ins.mnemonic,ins.op_str))
for t,n in targets.items():
    print("=== %s (IAT 0x%X) : %d ==="%(n,t,len(hits[t])))
    for r,m,op in hits[t]: print("   0x%06X %-18s %s"%(r,m,op))
