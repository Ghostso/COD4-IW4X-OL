import sys, pickle, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C = PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
def fs(r):
    i=bisect.bisect_right(prologues,r)-1; return prologues[i] if i>=0 else None
def callers(t):
    return sorted(set((s,k,fs(s)) for s,k,tg in edges if tg==t))
def dump(a,n,lim,tag):
    print("="*72); print("%s  func 0x%X"%(tag,a)); print("callers:", ", ".join("0x%X %s in 0x%X"%(s,k,f) for s,k,f in callers(a)) or "(none)"); print("-"*72)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+lim], C.IB+a):
        r=ins.address-C.IB; mark=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==X86_OP_IMM: mark=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
        print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,mark))
    print()
dump(0x351710,400,0x220,"0x351710")
dump(0x3518C0,400,0x220,"0x3518C0")
dump(0x352FC0,60,0x100,"post-body fn #1")
dump(0x3530E0,120,0x260,"post-body fn #2")
