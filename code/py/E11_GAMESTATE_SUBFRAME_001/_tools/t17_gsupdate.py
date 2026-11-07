# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fstart(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t):
    return sorted(set((s,k,fstart(s)) for s,k,tg in edges if tg==t))
for t in (0xA2980,0xA29E0,0x356580,0x356D80,0x354840,0x3530E0,0x3537D0,0x352FC0,0x3532F0):
    print("0x%06X callers:"%t)
    cs=callers(t)
    if not cs: print("    (none)")
    for s,k,f in cs: print("    site 0x%06X %s in 0x%06X"%(s,k,f))
print()
f=fstart(0x56892)
print("func containing 0x56892:", hex(f))
for s,k,ff in callers(f): print("    site 0x%06X %s in 0x%06X"%(s,k,ff))
