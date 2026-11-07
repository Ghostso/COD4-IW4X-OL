# -*- coding: utf-8 -*-
import sys,pefile
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=pefile.PE(p,fast_load=False)
mp={}
for e in getattr(C,"DIRECTORY_ENTRY_IMPORT",[]):
    for imp in e.imports:
        nm=imp.name.decode(errors="replace") if imp.name else "ord_%d"%imp.ordinal
        mp[imp.address]=(e.dll.decode(errors="replace"),nm)
print("0xbae4d4 =",mp.get(0xbae4d4))
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
C2=PE(p); md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print()
print("=== verify E-13 claim: .tvm0 call at 0x787982 ===")
o,_=C2.off(0x787960)
for ins in md.disasm(C2.d[o:o+0x60],C2.IB+0x787960):
    r=ins.address-C2.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C2.IB)&0xffffffff)
    print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
