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
print("0x245CE0 callers:",[(hex(s),hex(f)) for s,k,f in callers(0x245CE0)][:8])
print("0x1B0430 callers:",[(hex(s),hex(f)) for s,k,f in callers(0x1B0430)][:8])
print("0x78772D callers:",[(hex(s),hex(f)) for s,k,f in callers(0x78772D)][:8])
def closure(root,depth):
    out=set(); q=collections.deque([(root,0)]); seen={root}
    while q:
        n,d=q.popleft()
        if d>=depth: continue
        for c in callees(n):
            out.add(c)
            if c not in seen: seen.add(c); q.append((c,d+1))
    return out
C6=closure(0x605220,6)
for t,n in [(0xA2660,'0xA2660'),(0x3547D0,'0x3547D0'),(0x350170,'0x350170'),(0x34FD80,'0x34FD80'),(0xA2E50,'0xA2E50')]:
    print("  %s in 0x605220 closure(6): %s"%(n,t in C6))
