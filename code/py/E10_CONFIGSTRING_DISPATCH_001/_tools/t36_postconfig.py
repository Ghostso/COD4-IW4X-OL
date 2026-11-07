# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# identify 0x3547D0 selector callers + entry of 0x3537D0 post-body and 0x354840
for a,b,tag in [(0x354840,0x3549C0,"post-config 0x354840"),(0x3549C0,0x354A60,"0x3549C0"),(0x3530E0,0x3532F0,"0x3530E0 part")]:
 print("="*72);print(tag);print("-"*72)
 o,_=C.off(a);k=0
 for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
  r=ins.address-C.IB;m=""
  if ins.mnemonic in ("call","jmp"):
   for op in ins.operands:
    if op.type==1:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m));k+=1
  if k>120: break
 print()
