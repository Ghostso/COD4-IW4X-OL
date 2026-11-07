# -*- coding: utf-8 -*-
import sys,pickle,bisect
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
sec=C.pe.sections[0];o,_=C.off(sec.VirtualAddress);text=C.d[o:o+sec.SizeOfRawData];base=C.IB+sec.VirtualAddress
hist=[]
out=[]
for ins in md.disasm(text,base):
 hist.append(ins)
 if len(hist)>9: hist.pop(0)
 if ins.mnemonic in ('cmp','sub') and any(op.type==X86_OP_IMM and op.imm==6 for op in ins.operands):
  r=ins.address-C.IB
  f=fstart(r)
  ctx=" ; ".join("%X %s %s"%(x.address-C.IB,x.mnemonic,x.op_str) for x in hist[-7:])
  out.append((r,f,ctx))
print("total cmp/sub==6:",len(out))
# group by function
from collections import Counter
print(Counter(f for _,f,_ in out).most_common(20))
print()
for r,f,ctx in out:
  if f and (0x60000<=f<0xB0000 or 0x340000<=f<0x360000 or 0x1AC000<=f<0x1B0000):
   print("[0x%06X in 0x%06X] %s"%(r,f,ctx))
