# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def show(P,a,b,tag):
 print("="*72);print("%s 0x%X..0x%X"%(tag,a,b));print("-"*72)
 o,_=P.off(a)
 for ins in md.disasm(P.d[o:o+(b-a)],P.IB+a):
  r=ins.address-P.IB;m=""
  if ins.mnemonic in("call","jmp"):
   for op in ins.operands:
    if op.type==1:m=" -> 0x%X"%((op.imm-P.IB)&0xffffffff)
  print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
 print()
show(C,0x1AC190,0x1AC1D0,"CLIENT MSG_InitReadOnly")
show(C,0x3537D0,0x353A00,"CLIENT post-body 0x3537D0")
show(S,0xA22E0,0xA2330,"SERVER gamestate tail 0xA22E0..0xA2330")
