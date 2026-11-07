# -*- coding: utf-8 -*-
import sys, struct, re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True

# 1) locate "mp" literals in client
pat=re.compile(rb"mp\x00")
hits=[]
for sec in C.pe.sections:
    if sec.SizeOfRawData==0: continue
    o,_=C.off(sec.VirtualAddress)
    raw=C.d[o:o+sec.SizeOfRawData]
    for m in pat.finditer(raw):
        va=C.IB+sec.VirtualAddress+m.start()
        hits.append((va,sec.Name.rstrip(b"\0").decode(errors="replace")))
print("client 'mp\\0' literals:",[(hex(v),n) for v,n in hits])

# 2) xref: immediate operands equal to target VAs
TARGETS={
 0xCB8378:"gamestateupdate %d",
 0x7C0B90:"server mp",
}
for va in [v for v,_ in hits]:
    TARGETS[va]="mp literal 0x%X"%va
print()
for va,name in TARGETS.items():
    print("=== refs to %s (0x%X) ==="%(name,va))
    sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
    text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
    n=0
    for ins in sweep(md,text,base):
        for op in ins.operands:
            if op.type==X86_OP_IMM and (op.imm & 0xffffffff)==va:
                print("   site 0x%06X  %s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str)); n+=1
    if n==0: print("   (none)")
