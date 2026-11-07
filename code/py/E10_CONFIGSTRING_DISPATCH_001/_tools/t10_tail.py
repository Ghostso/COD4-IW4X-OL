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
def show(a,b,tag):
 print("="*72);print("%s 0x%X..0x%X"%(tag,a,b));print("-"*72)
 o,_=C.off(a)
 for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
  r=ins.address-C.IB;m=""
  if ins.mnemonic in("call","jmp"):
   for op in ins.operands:
    if op.type==X86_OP_IMM:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
 print()
show(0x352F80,0x352FC0,"0x352F80 entry (jmp to A2660)")
# exact bytes at the two jumps
for a in (0x352FA7,0x352FB4):
 o,_=C.off(a); print("site 0x%X bytes=%s"%(a,C.d[o:o+5].hex()))
show(0x6B5B0,0x6B690,"caller of 0x69C40 (0x6B5B0)")
show(0x56200,0x564A0,"caller of 0x69CE0 (0x56200)")
show(0x60410,0x60B60,"caller of 0x5E350 (0x60410)")
