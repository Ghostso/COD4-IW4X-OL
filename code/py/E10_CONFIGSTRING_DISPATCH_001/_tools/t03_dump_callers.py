import sys, pickle, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *

C = PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
D = pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl","rb"))
edges = D["edges"]; prologues = D["prologues"]; insn_addrs = D["insn_addrs"]

def func_start(rva):
    i = bisect.bisect_right(prologues, rva) - 1
    return prologues[i] if i >= 0 else None

def callers_of(t):
    out=[]
    for site,kind,tgt in edges:
        if tgt == t:
            out.append((site, kind, func_start(site)))
    return out

def dis(rva, n=200, limit_bytes=0x400):
    o,_ = C.off(rva)
    if o is None: return []
    r=[]
    k=0
    for ins in md.disasm(C.d[o:o+limit_bytes], C.IB+rva):
        r.append(ins); k+=1
        if k>=n: break
    return r

def dump(rva, n=400, limit=0x800, tag=""):
    print("="*70)
    print("FUNC 0x%X  %s" % (rva, tag))
    print("callers:", ", ".join("0x%X(%s,in 0x%X)"%(s,k,fs) for s,k,fs in callers_of(rva)) or "(none)")
    print("-"*70)
    for ins in dis(rva,n,limit):
        mark=""
        if ins.mnemonic in ("call","jmp"):
            for op in ins.operands:
                if op.type==X86_OP_IMM:
                    mark=" -> 0x%X" % ((op.imm-C.IB)&0xffffffff)
        print("  %06X %-16s %s%-22s%s" % (ins.address-C.IB, bytes(ins.bytes).hex(), ins.mnemonic+" ", ins.op_str, mark))
    print()

for rva,tag in [(0x3512A0,"caller #1"),(0x352E80,"caller #2/#3")]:
    dump(rva, 500, 0x1400, tag)
