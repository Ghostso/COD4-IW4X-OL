# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# ---- server WriteByte primitive region
print("=== SERVER 0x99530..0x99590 disasm ===")
o,_=S.off(0x99530)
k=0
for ins in md.disasm(S.d[o:o+0x60],S.IB+0x99530):
 r=ins.address-S.IB;m=""
 if ins.mnemonic=="call":
  for op in ins.operands:
   if op.type==1:m=" -> 0x%X"%((op.imm-S.IB)&0xffffffff)
 print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m));k+=1
print()
print("=== SERVER 0x99651 WriteLenStr + 0x99590 WriteBits head ===")
o,_=S.off(0x99590)
k=0
for ins in md.disasm(S.d[o:o+0x40],S.IB+0x99590):
 r=ins.address-S.IB;m=""
 if ins.mnemonic=="call":
  for op in ins.operands:
   if op.type==1:m=" -> 0x%X"%((op.imm-S.IB)&0xffffffff)
 print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m));k+=1
print()
# ---- client: all cmp/test with immediate 4 or 6 in regions of interest, with 6-insn context
regions=[(0x3512A0,0x351A30,"path1 0x3512A0"),(0x352F80,0x353A00,"path2 0x352F80/3546F3"),(0x354100,0x3547D0,"dispatcher"),(0xA2660,0xA29A0,"body reader")]
for a,b,tag in regions:
 print("=== %s : byte-value compares to 4/6 ==="%tag)
 o,_=C.off(a); hist=[]
 for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
  hist.append(ins)
  if len(hist)>7: hist.pop(0)
  if ins.mnemonic in ("cmp","test","sub","and"):
   imms=[op.imm for op in ins.operands if op.type==1]
   if any(v in (4,6) for v in imms):
    ctx=" | ".join("%X:%s %s"%(x.address-C.IB,x.mnemonic,x.op_str) for x in hist)
    print("   %s"%ctx)
 print()
