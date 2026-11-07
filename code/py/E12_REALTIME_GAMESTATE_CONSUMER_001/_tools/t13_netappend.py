# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
# 0x3524C0-ish region: find the function containing 0x3524FE
for addr in (0x3524FE,0x35252D,0x3523B7,0x3523CA):
    print("0x%X in func 0x%X"%(addr,fs(addr)))
print()
# disasm the function
a=0x3523A0
o,_=C.off(a)
for ins in md.disasm(C.d[o:o+0x120],C.IB+a):
    r=ins.address-C.IB; m=""
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==1: m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
    print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
print()
for t in (0x3523A0,0x3524C0,0x3524A0):
    cs=sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
    print("callers of 0x%06X: %s"%(t,[(hex(s),k,hex(f)) for s,k,f in cs]))
