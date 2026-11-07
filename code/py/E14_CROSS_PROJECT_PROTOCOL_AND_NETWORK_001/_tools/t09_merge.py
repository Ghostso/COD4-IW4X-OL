# -*- coding: utf-8 -*-
import sys,struct,pickle,bisect,collections
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callees(f):
    return sorted(set(tg for s,k,tg in edges if fs(s)==f))
def callers(t):
    return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def closure(root,depth):
    out=set(); q=collections.deque([(root,0)]); seen={root}
    while q:
        n,d=q.popleft()
        if d>=depth: continue
        for c in callees(n):
            out.add(c)
            if c not in seen: seen.add(c); q.append((c,d+1))
    return out
a=closure(0x605220,6); b=closure(0x6029A0,6)
print("0x605220 closure(6):",len(a))
print("0x6029A0 closure(6):",len(b))
sh=sorted(a&b)
print("shared count:",len(sh))
print("shared:",[hex(x) for x in sh[:20]])
print()
for t in (0x602BC0,0x612E80,0x5FB510,0x6104D0):
    print("callers of 0x%06X: %s"%(t,[(hex(s),k,hex(f)) for s,k,f in callers(t)][:8]))
