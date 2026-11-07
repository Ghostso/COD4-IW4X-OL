import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
print("func of 0x788133 = 0x%06X"%fs(0x788133))
# find true entry by scanning backward for push ebp; mov ebp,esp
o,_=C.off(0x787700)
last=None
for ins in md.disasm(C.d[o:o+0xB00],C.IB+0x787700):
    r=ins.address-C.IB
    if ins.mnemonic=="push" and ins.op_str=="ebp": last=r
    if r==0x788133: break
print("nearest push ebp before 0x788133: 0x%06X"%last)
# Is 0x788133's function the same as 0x6ABBC0's cluster? check shared callee
print("callees of 0x%06X: %s"%(fs(0x788133),sorted(set(hex(t) for s,k,t in edges if fs(s)==fs(0x788133)))[:12]))
print()
# does 0x6ABBC0 cluster share anything with 0x788133 cluster?
a=set(); import collections
def callees(f): return sorted(set(tg for s,k,tg in edges if fs(s)==f))
q=collections.deque([(0x6ABBC0,0)]); seen={0x6ABBC0}
while q:
    n,d=q.popleft()
    if d>=4: continue
    for c in callees(n):
        a.add(c)
        if c not in seen: seen.add(c); q.append((c,d+1))
b=set(); q=collections.deque([(fs(0x788133),0)]); seen={fs(0x788133)}
while q:
    n,d=q.popleft()
    if d>=4: continue
    for c in callees(n):
        b.add(c)
        if c not in seen: seen.add(c); q.append((c,d+1))
print("6ABBC0 closure(4)=%d  788133 closure(4)=%d  shared=%s"%(len(a),len(b),[hex(x) for x in (a&b)][:10]))
