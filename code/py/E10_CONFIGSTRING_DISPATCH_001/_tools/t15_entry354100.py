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
def callers(t): return sorted(set((s,k,fstart(s)) for s,k,tg in edges if tg==t))
def show(a,b,tag):
 print("="*72);print("%s 0x%X..0x%X"%(tag,a,b));print("callers:",[(hex(s),k,hex(f)) for s,k,f in callers(a)][:20]);print("-"*72)
 o,_=C.off(a)
 for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
  r=ins.address-C.IB;m=""
  if ins.mnemonic in("call","jmp"):
   for op in ins.operands:
    if op.type==X86_OP_IMM:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
 print()
show(0x354100,0x354300,"entry of function containing 0x3546F3")
print("callers of 0x354100:",[(hex(s),k,hex(f)) for s,k,f in callers(0x354100)])
print("callers of 0x1AC190:",[(hex(s),k,hex(f)) for s,k,f in callers(0x1AC190)][:40])
