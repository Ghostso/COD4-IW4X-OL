import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# strings referenced by 0x6ABxxx cluster
for va in (0xB98496,0xB98400,0xB98500):
    b=C.bytes_rva(va-0x400000,64)
    print("  0x%X %r"%(va,b[:56] if b else None))
print()
# find all string immediates in 0x6A8000..0x6AC000
import collections
found=collections.OrderedDict()
for a in range(0x6A8000,0x6AC000,1):
    o,_=C.off(a)
    if o is None: break
print("scan cluster for push imm in .rdata ranges")
o,_=C.off(0x6A8000)
for ins in md.disasm(C.d[o:o+0x4000],C.IB+0x6A8000):
    for op in ins.operands:
        if op.type==1 and 0xC00000<=op.imm<=0xD60000:
            b=C.bytes_rva(op.imm-0x400000,64)
            if b:
                s=b.split(b"\0")[0]
                if len(s)>=4: found[op.imm]=s[:56]
for va,s in list(found.items())[:30]:
    print("  0x%X %r"%(va,s))
