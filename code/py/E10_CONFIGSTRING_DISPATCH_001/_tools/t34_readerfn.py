import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
for a,n,tag in [(0x34F090,0x60,"0x89244 target 0x34F090"),(0x34FD80,0x40,"0x34FD80"),(0x3511C0,0x40,"0x3511C0")]:
 print("=== %s ==="%tag)
 o,_=C.off(a)
 for ins in md.disasm(C.d[o:o+n],C.IB+a):
  r=ins.address-C.IB;m=""
  if ins.mnemonic=="call":
   for op in ins.operands:
    if op.type==1:m=" -> 0x%X"%((op.imm-C.IB)&0xffffffff)
  print("  %06X %-20s %s %s%s"%(r,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str,m))
 print()
