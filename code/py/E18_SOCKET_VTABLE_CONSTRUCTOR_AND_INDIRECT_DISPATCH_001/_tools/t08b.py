# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
for va,tag in [(0x783F00,"0x783F00"),(0x783B70,"0x783B70")]:
    rva=va-0x400000
    print("=== %s nonzero string/immediate refs ==="%tag)
    o,_=C.off(rva)
    for ins in md.disasm(C.d[o:o+0x200],C.IB+rva):
        for op in ins.operands:
            if op.type==1 and 0xC00000<=op.imm<=0xD60000:
                b=C.bytes_rva(op.imm-0x400000,60)
                if b and len(b.split(b"\0")[0])>=4:
                    print("   0x%06X 0x%X %r"%(ins.address-0x400000,op.imm,b.split(b"\0")[0][:56]))
    print()
