import sys, collections, bisect
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=C.off(0x1000); text=C.d[o:o+C.pe.sections[0].SizeOfRawData]
seq=[]
for ins in sweep(md, text, C.IB+0x1000): seq.append((ins.address-C.IB,ins.id,ins.mnemonic,ins.op_str))
starts=[r for r,i,m,op in seq if m=="push" and op=="ebp"]
def fs(a):
    i=bisect.bisect_right(starts,a)-1; return starts[i] if i>=0 else None
RB=0x1AC670
cs=[(r,fs(r)) for r,i,m,op in seq if i==X86_INS_CALL for _ in [0]]
# recompute properly
cs=[]
for r,i,m,op in seq:
    if i==X86_INS_CALL and op.startswith("0x"):
        try: t=int(op,16)-C.IB
        except: continue
        if t==RB: cs.append((r,fs(r)))
byf=collections.defaultdict(list)
for a,f in cs: byf[f].append(a)
print("MSG_ReadBits total callers:",len(cs)," distinct containing funcs:",len(byf))
print()
print("=== containing functions sorted by RVA (caller count) ===")
for f in sorted(byf): print("   0x%06X : %d" % (f,len(byf[f])))