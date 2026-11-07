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
print("=== around 0x34E1A1 (data ref to 0x34E7C0) ===")
o,_=C.off(0x34E180)
for ins in md.disasm(C.d[o:o+0x60],C.IB+0x34E180):
    r=ins.address-C.IB
    print("  %06X %-22s %s"%(r,ins.mnemonic,ins.op_str))
print()
print("func containing 0x34E1A1: 0x%06X"%fs(0x34E1A1))
print()
# Does 0x34E7C0 get called indirectly? check callers of its container
for t in (0x34E7C0,0x34E1A1):
    pass
# Search for MSG_ReadData calls with non-constant length near string handling
print("=== callers of 0x1AC1D0 (MSG_ReadData) ===")
cs=sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==0x1AC1D0))
for s,k,f in cs: print("   site 0x%06X %s in 0x%06X"%(s,k,f))
