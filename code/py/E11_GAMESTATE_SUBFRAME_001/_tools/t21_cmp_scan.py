# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
regions=[(0x60000,0x70000,"0x60000-0x6FFFF"),(0xA0000,0xA3000,"0xA0000-0xA2FFF"),(0x340000,0x360000,"0x340000-0x35FFFF"),(0x1AC000,0x1B0000,"0x1AC000-0x1AFFFF")]
hist=[]; hits=[]
for ins in sweep(md,text,base):
    hist.append(ins)
    if len(hist)>10: hist.pop(0)
    if ins.mnemonic in ("cmp","sub"):
        imms=[op.imm for op in ins.operands if op.type==X86_OP_IMM]
        if any(v in (3,6,9,10) for v in imms):
            r=ins.address-C.IB
            for lo,hi,tag in regions:
                if lo<=r<hi:
                    # look back for a byte read
                    prev=" | ".join("%X:%s %s"%(x.address-C.IB,x.mnemonic,x.op_str) for x in hist[-6:-1])
                    hits.append((tag,r,ins.mnemonic+" "+ins.op_str,prev))
                    break
from collections import Counter
print("hits by region:",Counter(h[0] for h in hits))
print()
for tag,r,m,prev in hits:
    print("[%s] 0x%06X  %s"%(tag,r,m))
    print("        prev: %s"%prev)
