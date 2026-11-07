import sys, pickle, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C = PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
D = pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"]; prologues=D["prologues"]
pmap={p:i for i,p in enumerate(prologues)}
def func_start(rva):
    i=bisect.bisect_right(prologues,rva)-1; return prologues[i] if i>=0 else None
def callers_of(t):
    return sorted(set((s,k,func_start(s)) for s,k,tg in edges if tg==t))
def dump(a,b,tag):
    print("="*72); print("%s  RVA 0x%X..0x%X"%(tag,a,b)); print("-"*72)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+(b-a)], C.IB+a):
        r=ins.address-C.IB
        mark=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==X86_OP_IMM: mark=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
        print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,mark))
    print()
for f,tag in [(0x3512A0,"caller#1 0x3512A0"),(0x352E80,"caller#2 0x352E80")]:
    print("callers of 0x%X:"%f)
    for s,k,fs in callers_of(f): print("   site 0x%X %s in 0x%X"%(s,k,fs))
dump(0x351480,0x351560,"site#1 around 0x3514F0")
dump(0x352F40,0x352FE0,"sites#2/#3 around 0x352FA7/0x352FB4")
dump(0x34E7C0,0x34E9A0,"upstream caller 0x34E7C0")
dump(0x3519F0,0x351A40,"upstream tail 0x3519F0/0x351A10")
