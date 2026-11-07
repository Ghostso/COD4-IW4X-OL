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
# build reverse map func -> set(func)
rev={}
for s,k,t in edges:
    f=fs(s)
    if f is None: continue
    rev.setdefault(t,set()).add(f)
# BFS upward from 0x350170
from collections import deque
start=0x350170
seen={start}; q=deque([(start,0)])
levels={0:[start]}
while q:
    node,d=q.popleft()
    if d>=4: continue
    for up in sorted(rev.get(node,[])):
        if up in seen: continue
        seen.add(up); q.append((up,d+1)); levels.setdefault(d+1,[]).append(up)
for d in sorted(levels):
    print("depth %d (%d funcs):"%(d,len(levels[d])))
    for f in sorted(levels[d]): print("   0x%06X"%f)
    print()
