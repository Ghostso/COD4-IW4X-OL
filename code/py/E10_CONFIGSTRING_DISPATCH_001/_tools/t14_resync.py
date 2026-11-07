# -*- coding: utf-8 -*-
import sys,pickle,bisect
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl","rb"))
prologues=D["prologues"]
def fstart(r):
 i=bisect.bisect_right(prologues,r)-1;return prologues[i] if i>=0 else None
print("fstart(0x3546F3)=0x%X"%fstart(0x3546F3))
a=0x3545C0;b=0x354780;o,_=C.off(a)
print("bytes at 0x3545C0:",C.d[o:o+16].hex())
for ins in sweep(md,C.d[o:o+(b-a)],C.IB+a):
 r=ins.address-C.IB;m=""
 if ins.mnemonic in("call","jmp"):
  for op in ins.operands:
   if op.type==X86_OP_IMM:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
 print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
