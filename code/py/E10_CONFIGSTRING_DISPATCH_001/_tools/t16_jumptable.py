# -*- coding: utf-8 -*-
import sys,struct,pickle,bisect
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
print("=== JUMP TABLE @ RVA 0x3547AC (VA 0x7547AC) ===")
o,_=C.off(0x3547AC)
for i in range(9):
 v=struct.unpack_from("<I",C.d,o+i*4)[0]
 rva=(v-C.IB)&0xffffffff
 print("  case %d -> VA 0x%08X  RVA 0x%06X  func_start 0x%06X"%(i,v,rva,fstart(rva) if rva<0x10000000 else -1))
print()
# disasm each target 40 insns
for i in range(9):
 v=struct.unpack_from("<I",C.d,o+i*4)[0]; rva=(v-C.IB)&0xffffffff
 print("="*72);print("CASE %d target 0x%X"%(i,rva));print("-"*72)
 oo,_=C.off(rva);k=0
 for ins in md.disasm(C.d[oo:oo+0x160],C.IB+rva):
  r=ins.address-C.IB;m=""
  if ins.mnemonic in("call","jmp"):
   for op in ins.operands:
    if op.type==X86_OP_IMM:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m));k+=1
  if k>=30:break
 print()
# upstream function 0x3547d0
print("="*72);print("UPSTREAM 0x3547D0");print("callers:",[(hex(s),k,hex(fstart(s))) for s,k,tg in edges if tg==0x3547D0])
oo,_=C.off(0x3547D0);k=0
for ins in md.disasm(C.d[oo:oo+0x200],C.IB+0x3547D0):
 r=ins.address-C.IB;m=""
 if ins.mnemonic in("call","jmp"):
  for op in ins.operands:
   if op.type==X86_OP_IMM:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
 print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m));k+=1
 if k>=60:break
