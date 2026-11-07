import sys,struct,bisect,pickle
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
def callers(f): return sorted(set(fs(s) for s,k,t in edges if fs(t)==f))
def callees(f): return sorted(set(t for s,k,t in edges if fs(s)==f))
def show(a,n,tag):
    print("="*72); print(tag,hex(a),hex(a+n)); print("-"*72)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+n],C.IB+a):
        print("%06X %-22s %s %s"%(ins.address-C.IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
show(0x6AAC80,0x500,"0x6AAC80..0x6AB180")
# find prologue before 0x6AAF94
for a in (0x6AAF94,0x6AAFC3,0x6AB0C8,0x6AB137):
    print("SITE",hex(a),"func",hex(fs(a)) if fs(a) else None,"callers",[hex(x) for x in callers(fs(a))] if fs(a) else [])
# direct callers of 0x6AACC0 region candidates
for f in sorted(set(fs(a) for a in (0x6AAF94,0x6AAFC3,0x6AB0C8,0x6AB137))):
    print("FUNC",hex(f),"callers",[hex(x) for x in callers(f)],"callees",[hex(x) for x in callees(f)])
