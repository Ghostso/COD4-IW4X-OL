# -*- coding: utf-8 -*-
import sys,pickle,bisect,collections
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t): return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def callees(f): return sorted(set(tg for s,k,tg in edges if fs(s)==f))
for t in (0x602BC0,0x612E80,0x605220,0x6104D0):
    print("callers of 0x%06X: %s"%(t,[(hex(s),k,hex(f)) for s,k,f in callers(t)][:10]))
print()
# BFS upward from 0x605220 to find whether it reaches main loop / net
seen={0x605220}; q=collections.deque([(0x605220,0)]); lv={0:[0x605220]}
while q:
    n,d=q.popleft()
    if d>=4: continue
    for s,k,f in callers(n):
        if f is None or f in seen: continue
        seen.add(f); q.append((f,d+1)); lv.setdefault(d+1,[]).append(f)
for d in sorted(lv):
    print("depth %d: %s"%(d,[hex(x) for x in lv[d]]))
