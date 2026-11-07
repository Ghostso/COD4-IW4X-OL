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
RECV=[(0x1B0430,"recvfrom"),(0x6B4DE0,"recvfrom"),(0x775AB0,"recvfrom"),(0x602430,"recv"),(0x6029A0,"recv"),(0x605220,"recv"),(0x775A50,"recv"),(0x784F60,"recv"),(0x78772D,"recv")]
for f,api in RECV:
    cs=callers(f)
    print("=== 0x%06X (%s) : %d direct callers ==="%(f,api,len(cs)))
    for s,k,c in cs: print("     site 0x%06X %s in 0x%06X"%(s,k,c))
    if not cs: print("     (none - reached only via pointer/table)")
    print()
