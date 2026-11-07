# -*- coding: utf-8 -*-
import sys,pefile,re
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=pefile.PE(p,fast_load=False); IB=C.OPTIONAL_HEADER.ImageBase
mp={}
for e in getattr(C,"DIRECTORY_ENTRY_IMPORT",[]):
    dll=e.dll.decode(errors="replace")
    for imp in e.imports:
        nm=imp.name.decode(errors="replace") if imp.name else "ord_%d"%imp.ordinal
        mp[imp.address]=(dll,nm)
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001\_tools")
from pe_helper import PE
C2=PE(p); md=None
from capstone import *
from capstone.x86 import *
from sweep import sweep
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C2.pe.sections[0]; o,_=C2.off(sec.VirtualAddress)
text=C2.d[o:o+sec.SizeOfRawData]; base=C2.IB+sec.VirtualAddress
# collect IAT addresses referenced within 0x1B0430..0x1B0F30
used={}
for ins in sweep(md,text,base):
    r=ins.address-C2.IB
    if 0x1B0430<=r<0x1B0F30:
        for op in ins.operands:
            if op.type==X86_OP_MEM and op.mem.disp in mp:
                used.setdefault(op.mem.disp,[]).append((r,ins.mnemonic,ins.op_str))
print("=== IAT APIs used in 0x1B0430..0x1B0F30 ===")
for a in sorted(used):
    dll,nm=mp[a]
    print("  0x%X %-12s %-24s used %d x  first@0x%06X"%(a,dll,nm,len(used[a]),used[a][0][0]))
