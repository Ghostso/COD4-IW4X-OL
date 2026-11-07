# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# decode 0x354100 with resync/linear from entry
def dis_entry(a,b,tag):
 print("="*72);print(tag);print("-"*72)
 o,_=C.off(a)
 k=0
 for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
  r=ins.address-C.IB;m=""
  if ins.mnemonic in("call","jmp"):
   for op in ins.operands:
    if op.type==1:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m));k+=1
 print("  decoded",k)
dis_entry(0x354100,0x3547AC,"FULL dispatcher 0x354100")
