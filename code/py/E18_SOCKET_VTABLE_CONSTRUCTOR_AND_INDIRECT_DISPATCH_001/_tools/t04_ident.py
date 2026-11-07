# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== strings 0x898630..0x898D00 ===")
o,_=C.off(0x898630)
raw=C.d[o:o+0x6D0]
for m in re.finditer(rb"[ -~]{4,}",raw):
    print("   0x%X %r"%(0x400000+0x898630+m.start(), m.group()[:80]))
print()
for a,b,t in [(0x775A50,0x775A80,"0x775A50"),(0x775A80,0x775AB0,"0x775A80"),(0x775AB0,0x775AF0,"0x775AB0")]:
    print("--- %s ---"%t)
    o2,_=C.off(a)
    for ins in md.disasm(C.d[o2:o2+(b-a)],C.IB+a):
        print("   %06X %-18s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
