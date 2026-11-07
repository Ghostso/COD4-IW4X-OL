# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== demo command string cluster 0xCD61A0-0xCD6290 ===")
o,_=C.off(0xCD61A0)
raw=C.d[o:o+0xF0]
p=0
while p<len(raw):
    e=raw.find(b"\0",p)
    if e<0: break
    if e>p:
        print("   0x%X %r"%(C.IB+0xCD61A0+p, raw[p:e].decode("latin-1")))
    p=e+1
print()
print("=== 0x34DF80 registration block ===")
o2,_=C.off(0x34E130)
for ins in md.disasm(C.d[o2:o2+0xC0],C.IB+0x34E130):
    r=ins.address-C.IB; m=""
    if ins.mnemonic=="call":
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
