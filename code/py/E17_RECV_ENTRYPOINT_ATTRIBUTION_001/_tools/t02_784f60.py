# -*- coding: utf-8 -*-
import sys,pefile
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(p)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
pe=pefile.PE(p,fast_load=False)
mp={}
for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    for imp in e.imports:
        nm=imp.name.decode(errors="replace") if imp.name else "ord_%d"%imp.ordinal
        mp[imp.address]=(e.dll.decode(errors="replace"),nm)
out=[]
o,_=C.off(0x784F60)
for ins in md.disasm(C.d[o:o+0x120],C.IB+0x784F60):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
            elif op.type==2 and op.mem.disp in mp:
                dll,nm=mp[op.mem.disp]; m=" -> %s!%s"%(dll,nm)
    out.append("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
print("\n".join(out))
