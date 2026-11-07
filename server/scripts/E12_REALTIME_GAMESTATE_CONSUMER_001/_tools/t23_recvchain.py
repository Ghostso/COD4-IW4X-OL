# -*- coding: utf-8 -*-
import sys,pickle,bisect,collections
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
sites=[0x1B0BA1,0x6B4E3C,0x775ADE,0x602441,0x6029BE,0x6052AB,0x775A6C,0x784F7D,0x788133]
for s in sites:
    print("  site 0x%06X in func 0x%06X"%(s,fs(s)))
print()
def callees(f):
    return sorted(set(tg for s,k,tg in edges if fs(s)==f))
for s in sites:
    f=fs(s)
    seen={f}; q=collections.deque([(f,0)]); found=[]
    while q:
        node,d=q.popleft()
        if d>=7: continue
        for c in callees(node):
            if c in (0x350170,0x3547D0,0x354100,0xA2660,0x34FD80,0x352F80):
                found.append((c,d+1,node))
            if c in seen: continue
            seen.add(c); q.append((c,d+1))
    print("recv func 0x%06X -> targets: %s"%(f,[(hex(t),d,hex(via)) for t,d,via in found][:8]))
