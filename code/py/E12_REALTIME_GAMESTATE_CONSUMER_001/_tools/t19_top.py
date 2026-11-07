# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t):
    return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def callees(f):
    return sorted(set((s,k,tg) for s,k,tg in edges if fs(s)==f))
print("callees of 0x34E7C0:")
for s,k,t in callees(0x34E7C0): print("   0x%06X %s -> 0x%06X"%(s,k,t))
print()
for t in (0x245CE0,0x1A9760,0x1A9060):
    cs=callers(t)
    print("callers of 0x%06X: %s"%(t,[(hex(s),k,hex(f)) for s,k,f in cs]))
