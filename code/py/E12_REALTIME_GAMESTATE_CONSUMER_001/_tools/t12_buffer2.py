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
targets=["0x8048","0x30af30","0x30af28","0x30af2c"]
hits={t:[] for t in targets}
n=0
for ins in sweep(md,text,base):
    n+=1
    for t in targets:
        if t in ins.op_str:
            hits[t].append((ins.address-C.IB,ins.mnemonic,ins.op_str))
print("scanned",n)
for t in targets:
    print("=== %s : %d ==="%(t,len(hits[t])))
    for r,m,op in hits[t][:40]:
        print("   %06X %-20s %s"%(r,m,op))
