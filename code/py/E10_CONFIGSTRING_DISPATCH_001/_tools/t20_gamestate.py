# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def show(a,b,tag):
 print("="*72);print("%s 0x%X..0x%X"%(tag,a,b));print("-"*72)
 o,_=S.off(a)
 for ins in md.disasm(S.d[o:o+(b-a)],S.IB+a):
  r=ins.address-S.IB;m=""
  if ins.mnemonic in("call","jmp"):
   for op in ins.operands:
    if op.type==1:m=" -> 0x%X"%((op.imm-S.IB)&0xffffffff)
  print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
 print()
show(0xA21B8,0xA2340,"_CODOL2697_WriteGamestate")
show(0x499551,0x499590,"server WriteByte 0x99551")
show(0xA2400,0xA24C0,"server 0xA23F0/0xA2480 region")
