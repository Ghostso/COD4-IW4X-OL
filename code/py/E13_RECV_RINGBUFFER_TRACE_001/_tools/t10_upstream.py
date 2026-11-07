# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t):
    return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
print("=== upstream of the 5 recv funcs that HAVE direct callers ===")
for f in (0x6B4DE0,0x602430,0x605220,0x784F60):
    for s,k,c in callers(f):
        print("  recv 0x%06X <- site 0x%06X in 0x%06X"%(f,s,c))
        # 2 more levels up
        for s2,k2,c2 in callers(c):
            print("         <- 0x%06X %s in 0x%06X"%(s2,k2,c2))
print()
# vtable region check
for va in (0x898580,0x898588,0x898590,0x898598):
    o,_=C.off(va)
    raw=C.d[o:o+0x20]
    vals=[hex(int.from_bytes(raw[i:i+4],'little')) for i in range(0,0x20,4)]
    print("  .rdata 0x%X: %s"%(va,vals))
