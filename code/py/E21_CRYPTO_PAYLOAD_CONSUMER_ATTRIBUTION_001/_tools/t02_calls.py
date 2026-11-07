import sys,struct,bisect,pickle,collections
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=PE(P); md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
def callers(f):
    return sorted(set(fs(s) for s,k,t in edges if fs(t)==f))
def callees(f):
    return sorted(set(t for s,k,t in edges if fs(s)==f))
def closure(root,depth):
    seen={root}; q=collections.deque([(root,0)])
    while q:
        n,d=q.popleft()
        if d>=depth: continue
        for c in callees(n):
            if c not in seen: seen.add(c); q.append((c,d+1))
    return seen
roots=[0x6A84E0,0x6A9720,0x6A9920,0x6A8570,0x6A85A0,0x6A83C0,0x6A82E0,0x6A88C0,0x6A8720]
for r in roots:
    print("ROOT",hex(r),"callers",[hex(x) for x in callers(r)])
    cl=closure(r,4)
    print("  closure4",len(cl),[hex(x) for x in sorted(cl)][:80])
print("---- target presence in closures ----")
T=[0xA2660,0xA2E50,0x350170,0x3547D0,0x354100,0x3524F0,0x352570,0x6ABBC0,0x6ABE80]
for r in roots:
    cl=closure(r,5)
    print(hex(r),[hex(t) for t in T if t in cl])
