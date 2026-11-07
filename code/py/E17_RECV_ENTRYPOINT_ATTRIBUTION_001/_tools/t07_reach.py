# -*- coding: utf-8 -*-
import sys,pickle,bisect,collections,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callees(f): return sorted(set(tg for s,k,tg in edges if fs(s)==f))
def callers(t): return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def closure(root,depth):
    out=set(); q=collections.deque([(root,0)]); seen={root}
    while q:
        n,d=q.popleft()
        if d>=depth: continue
        for c in callees(n):
            out.add(c)
            if c not in seen: seen.add(c); q.append((c,d+1))
    return out
for root in (0x6B3310,0x6ABBC0,0x6A9920,0x783F00,0x783B70):
    cl=closure(root,7)
    hit=[(hex(t),t in cl) for t in (0xA2660,0x3547D0,0x354100,0x350170,0x34FD80,0xA2E50,0x3524F0,0x352570)]
    print("  root 0x%06X closure(7)=%d"%(root,len(cl)))
    print("     %s"%hit)
print("upstream 0x6B3310:",[(hex(s),hex(f)) for s,k,f in callers(0x6B3310)][:8])
