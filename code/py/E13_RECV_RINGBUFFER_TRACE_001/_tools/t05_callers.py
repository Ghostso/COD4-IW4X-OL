# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t):
    return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def callees(f):
    return sorted(set((s,k,tg) for s,k,tg in edges if fs(s)==f))
for t in (0x351D00,0x3524F0,0x352570,0x34FD80,0x350170):
    print("callers of 0x%06X:"%t)
    cs=callers(t)
    if not cs: print("     (none)")
    for s,k,f in cs: print("     0x%06X %s in 0x%06X"%(s,k,f))
print()
print("callees of 0x351D00 (unique targets):")
for t in sorted(set(t for s,k,t in callees(0x351D00))): print("   0x%06X"%t)
