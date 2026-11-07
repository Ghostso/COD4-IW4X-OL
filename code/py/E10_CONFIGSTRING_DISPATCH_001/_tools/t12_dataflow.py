# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl","rb"))
edges=D["edges"];prologues=D["prologues"]
def fstart(r):
 i=bisect.bisect_right(prologues,r)-1;return prologues[i] if i>=0 else None
def callers(t): return sorted(set((s,k) for s,k,tg in edges if tg==t))
def show(a,b,tag,maxn=400):
 print("="*72);print("%s 0x%X..0x%X"%(tag,a,b));print("CALLERS:",[(hex(s),k) for s,k in callers(a)][:20]);print("-"*72)
 o,_=C.off(a);n=0
 for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
  r=ins.address-C.IB;m=""
  if ins.mnemonic in("call","jmp"):
   for op in ins.operands:
    if op.type==X86_OP_IMM:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m));n+=1
 print()
show(0x3512A0,0x351490,"0x3512A0 up to call site",120)
show(0x352F80,0x352FBC,"0x352F80 tail-jump shim",40)
for f in (0x3512A0,0x352F80):
 print("callers of 0x%X: %s"%(f,[(hex(s),k) for s,k in callers(f)]))
show(0x569A0,0x569F0,"0x69A50",40)
