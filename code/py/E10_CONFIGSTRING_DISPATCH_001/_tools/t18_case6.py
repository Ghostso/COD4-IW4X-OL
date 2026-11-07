# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def show(a,b,tag):
 print("="*72);print("%s 0x%X..0x%X"%(tag,a,b));print("-"*72)
 o,_=C.off(a)
 for ins in md.disasm(C.d[o:o+(b-a)],C.IB+a):
  r=ins.address-C.IB;m=""
  if ins.mnemonic in("call","jmp","je","jne","jz","jnz","jg","jge","jl","jle","ja","jae","jb","jbe"):
   for op in ins.operands:
    if op.type==1:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  print("  %06X %-22s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
 print()
show(0x354560,0x3546B0,"case 6 prelude 0x354560..0x3546B0")
show(0x354697,0x3546C4,"case 6 entry 0x354697")
# 0x3547d0 whole
show(0x3547D0,0x35483E,"selector loop 0x3547D0")
# read primitive used via [edi+0x89244] -- identify it: find assignments to 0x89244
print("=== search immediate stores to +0x89244 ===")
import pickle,bisect
D=pickle.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_work\client_callgraph.pkl","rb"))
# scan text for 0x89244 displacement pattern
sec=C.pe.sections[0];o,_=C.off(sec.VirtualAddress);text=C.d[o:o+sec.SizeOfRawData];base=C.IB+sec.VirtualAddress
for ins in md.disasm(text,base):
 if '0x89244' in ins.op_str and ins.mnemonic in ('mov','lea'):
  print("  %06X %-16s %s"%(ins.address-C.IB,ins.mnemonic,ins.op_str))
