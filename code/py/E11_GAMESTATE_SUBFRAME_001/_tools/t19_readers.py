# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# precise: identify MSG struct offsets for client reader used by 0x352570
# 0x352570 signature: (dst, len, handle) ; it copies into global ring buffer at [edi+0x8048]
# Let's find callers of 0x352570 and their lengths
import pickle,bisect
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fstart(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
print("callers of 0x352570:")
for s,k,t in sorted(set((s,k,fstart(s)) for s,k,t in edges if t==0x352570)):
    print("   site 0x%06X %s in 0x%06X"%(s,k,t))
print()
print("callers of 0x34F090 (demo reader):")
for s,k,t in sorted(set((s,k,fstart(s)) for s,k,t in edges if t==0x34F090)):
    print("   site 0x%06X %s in 0x%06X"%(s,k,t))
