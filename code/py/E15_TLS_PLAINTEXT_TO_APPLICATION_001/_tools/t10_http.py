# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print("=== strings referenced in 0x612E80 and 0x600630 regions ===")
for a,b,tag in [(0x612E80,0x613040,"0x612E80"),(0x600630,0x600900,"0x600630"),(0x601270,0x601450,"0x601270")]:
    print("--- %s ---"%tag)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
        if ins.mnemonic=="push":
            for op in ins.operands:
                if op.type==1 and 0xC00000<=op.imm<=0xD40000:
                    bb=C.bytes_rva(op.imm-C.IB,70)
                    if bb: print("   0x%06X push 0x%X %r"%(ins.address-C.IB,op.imm,bb.split(b"\0")[0][:64]))
print()
print("=== strings near the TLS/HTTP cluster: list interesting ===")
o,_=C.off(0xC38900)
raw=C.d[o:o+0x200]
for m in re.finditer(rb"[ -~]{5,}",raw):
    print("   0x%X %r"%(C.IB+0xC38900+m.start(), m.group()[:70]))
