import sys,pickle,bisect,collections,struct,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
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
TGT={0xA2660:'0xA2660',0xA2E50:'0xA2E50',0x350170:'0x350170',0x3547D0:'0x3547D0',0x354100:'0x354100',0x3524F0:'0x3524F0',0x352570:'0x352570'}
for root in (0x6A9920,0x6A84E0,0x6A9720,0x6A9260,0x6ABBC0):
    cl=closure(root,5)
    hits=[TGT[t] for t in TGT if t in cl]
    print("root 0x%06X closure(5)=%d game-hits=%s"%(root,len(cl),hits or 'NONE'))
print()
print("=== vtables used by 0x6A84E0 ctor ===")
for va in (0xC5B0A4,0xCBBD1C):
    o,_=C.off(va-0x400000)
    slots=[struct.unpack_from("<I",C.d,o+i*4)[0] for i in range(6)]
    print("  0x%X: %s"%(va,[hex(s) for s in slots]))
    # string near
    for d in range(-0x40,0x80,4):
        off=va-0x400000+d
        ob,_=C.off(off)
        if ob is None: continue
        b=C.d[ob:ob+48]
        s=b.split(b'\0')[0]
        if 6<=len(s)<=44 and all(32<=c<127 for c in s):
            print("     near 0x%X %r"%(off,s))
