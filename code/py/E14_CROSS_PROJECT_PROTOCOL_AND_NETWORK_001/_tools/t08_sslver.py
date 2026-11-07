# -*- coding: utf-8 -*-
import sys,struct,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== OpenSSL version / error strings ===")
found=0
for s in C.pe.sections:
    if s.SizeOfRawData==0: continue
    o,_=C.off(s.VirtualAddress); raw=C.d[o:o+s.SizeOfRawData]
    for pat in [rb"OpenSSL [0-9][^\x00]{0,40}", rb"SSL routines[^\x00]{0,40}"]:
        for m in list(re.finditer(pat,raw))[:4]:
            va=C.IB+s.VirtualAddress+m.start()
            print("  0x%X %r"%(va,raw[m.start():m.start()+56]))
            found+=1
print("  found:",found)
print()
print("=== CODOL netchan constants present in CLIENT? ===")
sec=C.pe.sections[0]; o2,_=C.off(sec.VirtualAddress)
text=C.d[o2:o2+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
for imm,label in [(0x489,"1161"),(0x70cc729,"118277929")]:
    hits=[]
    for ins in sweep(md,text,base):
        if ins.mnemonic in ("cmp","mov"):
            for op in ins.operands:
                if op.type==X86_OP_IMM and op.imm==imm:
                    hits.append(ins.address-C.IB)
    print("  %s (0x%X): %d hits %s"%(label,imm,len(hits),["0x%X"%h for h in hits[:6]]))
