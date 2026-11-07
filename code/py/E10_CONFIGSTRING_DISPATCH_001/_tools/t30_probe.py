# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# --- client strings in regions
print("=== client string probes near dispatcher/paths ===")
for rva,n in [(0xCB3894,64),(0xCB7770,64),(0xCD6384,64),(0xCB8378,32)]:
 b=C.bytes_rva(rva,n)
 print("  0x%X %r"%(rva,b.split(b"\0")[0] if b else None))
# --- search all refs to the union of 0x06 writers/readers (as imm)
print()
print("=== client absolute refs to constants 4 & 6 in .text (mov/cmp/push) near reader ===")
for a,b in [(0x350000,0x360000),(0xA2000,0xA3000)]:
 o,_=C.off(a); k=0
 for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
  if ins.mnemonic in ('push','cmp') and any(op.type==1 and op.imm in (4,6) for op in ins.operands):
   r=ins.address-C.IB
   print("  0x%06X %-16s %s"%(r,ins.mnemonic,ins.op_str)); k+=1
 print("  region 0x%X-0x%X count=%d"%(a,b,k))
print()
# --- dump client 0x3512A0 tail (0x351560-0x351A30) to see second A2660 use and surrounding ops
print("=== client 0x351500..0x351A30 (path1 tail) ===")
o,_=C.off(0x351500);k=0
for ins in md.disasm(C.d[o:o+0x530],C.IB+0x351500):
 r=ins.address-C.IB;m=""
 if ins.mnemonic in ("call","jmp"):
  for op in ins.operands:
   if op.type==1:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
 print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m));k+=1
