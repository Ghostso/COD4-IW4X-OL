# -*- coding: utf-8 -*-
import sys,pickle,bisect,struct
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
# Exact disasm windows of the three real call sites with 25 instructions before
def ctx(site,before=30,after=14,tag=""):
 print("="*72);print("%s SITE 0x%X"%(tag,site));print("-"*72)
 o,_=C.off(site-before)
 insns=list(md.disasm(C.d[o:o+200],C.IB+site-before))
 # print instructions overlapping [site-? site+after]
 for ins in insns:
  r=ins.address-C.IB
  if r>site+after: break
  if r<site-before+0: continue
  m=""
  if ins.mnemonic in("call","jmp"):
   for op in ins.operands:
    if op.type==X86_OP_IMM:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  mark="   <== TARGET SITE" if r==site else ""
  print("  %06X %-22s %s %s%s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m,mark))
 print()
ctx(0x3514F0,34,12,"#1")
ctx(0x352FA7,30,8,"#2")
ctx(0x352FB4,30,8,"#3")
# Who calls the readers 0x352570 with what lengths
print("0x352570 callers:",[(hex(s),k,hex(f)) for s,k,f in callers(0x352570)])
