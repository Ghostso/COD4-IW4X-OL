# -*- coding: utf-8 -*-
import sys,pickle,bisect,collections
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1
    return prologues[i] if i>=0 else None
RECV=[0x1B0430,0x6B4DE0,0x775AB0,0x602430,0x6029A0,0x605220,0x775A50,0x784F60,0x78772D]
byfunc=collections.defaultdict(list)
for s,k,t in edges:
    byfunc[fs(s)].append((s,k,t))
# collect all funcs within 3 levels
allf=set(RECV)
for f in list(RECV):
    seen={f}; q=collections.deque([(f,0)])
    while q:
        node,d=q.popleft()
        if d>=3: continue
        for s,k,t in byfunc.get(node,[]):
            allf.add(t)
            if t in seen: continue
            seen.add(t); q.append((t,d+1))
print("total funcs in 3-level closure:",len(allf))
# Now scan .text for accesses to ring buffer globals, and record which func they're in
sec=C.pe.sections[0]; o,_=C.off(sec.VirtualAddress)
text=C.d[o:o+sec.SizeOfRawData]; base=C.IB+sec.VirtualAddress
pats=["0x743de9c","0x30af2c","0x30af30","0x8048"]
hits=[]
for ins in sweep(md,text,base):
    for p in pats:
        if p in ins.op_str:
            f=fs(ins.address-C.IB)
            hits.append((ins.address-C.IB,f,p,ins.mnemonic,ins.op_str))
            break
print("total ring-global refs in whole .text:",len(hits))
print()
inclosure=[h for h in hits if h[1] in allf]
print("ring-global refs INSIDE 3-level closure:",len(inclosure))
for r,f,p,m,op in inclosure:
    print("   0x%06X (func 0x%06X) [%s] %s %s"%(r,f,p,m,op))
print()
# also check indirect calls (call reg/mem) inside closure
print("=== indirect call/jmp sites inside closure ===")
n=0
for ins in sweep(md,text,base):
    if ins.mnemonic in ("call","jmp"):
        f=fs(ins.address-C.IB)
        if f in allf:
            ind=any(op.type in (X86_OP_REG,X86_OP_MEM) for op in ins.operands)
            if ind:
                print("   0x%06X (func 0x%06X) %s %s"%(ins.address-C.IB,f,ins.mnemonic,ins.op_str)); n+=1
print("indirect count:",n)
