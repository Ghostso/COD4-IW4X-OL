# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
print("=== 0x60E470 (callback passed to 0x60E5B0) ===")
o,_=C.off(0x60E470)
for ins in md.disasm(C.d[o:o+0x30],C.IB+0x60E470):
    print("  %06X %-22s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
print()
print("=== callers of 0x60E4A0 / 0x60E500 ===")
for t in (0x60E4A0,0x60E500,0x602760,0x602600,0x6025A0):
    cs=sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
    print("  0x%06X : %s"%(t,[(hex(s),k,hex(f)) for s,k,f in cs]))
print()
print("=== callers of 0x6029A0 (recv wrapper) already known; check 0x602760 body head ===")
o2,_=C.off(0x602760)
for ins in md.disasm(C.d[o2:o2+0x90],C.IB+0x602760):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
