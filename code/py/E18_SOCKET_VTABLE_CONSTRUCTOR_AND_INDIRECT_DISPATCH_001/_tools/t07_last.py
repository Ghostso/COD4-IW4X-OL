# -*- coding: utf-8 -*-
import sys,struct,pickle,bisect,collections
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(t): return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def callees(f): return sorted(set(tg for s,k,tg in edges if fs(s)==f))
def closure(root,depth):
    out=set(); q=collections.deque([(root,0)]); seen={root}
    while q:
        n,d=q.popleft()
        if d>=depth: continue
        for c in callees(n):
            out.add(c)
            if c not in seen: seen.add(c); q.append((c,d+1))
    return out
for rva in (0x776130,0x776170,0x7763A0,0x7767C0,0x7767E0,0x776B50,0x776F00):
    print("  0x%06X callers: %s"%(rva,[(hex(s),hex(f)) for s,k,f in callers(rva)][:6]))
print()
for slot in (0x898588,0x898590):
    o,_=C.off(slot)
    v=struct.unpack_from("<I",C.d,o)[0]
    print("  slot 0x%X = VA 0x%08X (RVA 0x%X)"%(slot,v,(v-0x400000)&0xffffffff))
print()
for root in (0x775A50,0x775AB0,0x776130,0x776170):
    cl=closure(root,6)
    hits=[hex(t) for t in (0xA2660,0x3547D0,0x354100,0x350170,0x34FD80,0xA2E50) if t in cl]
    print("  root 0x%06X closure(6)=%d game-hits=%s"%(root,len(cl),hits))
