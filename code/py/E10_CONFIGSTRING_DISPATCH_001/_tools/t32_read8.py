# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
sec=C.pe.sections[0];o,_=C.off(sec.VirtualAddress);text=C.d[o:o+sec.SizeOfRawData];base=C.IB+sec.VirtualAddress
hist=[];hits=[]
for ins in md.disasm(text,base):
 hist.append(ins)
 if len(hist)>16: hist.pop(0)
 if ins.mnemonic=='call':
  for op in ins.operands:
   if op.type==1:
    tgt=(op.imm-C.IB)&0xffffffff
    if tgt in (0x1AC670,0x1AC1D0):
     p=None
     for x in reversed(hist[:-1]):
      if x.mnemonic=='push':
       for oo in x.operands:
        if oo.type==1:p=oo.imm
       break
      if x.mnemonic in ('call','ret'):break
     hits.append((ins.address-C.IB,tgt,p))
print("total:",len(hits))
from collections import Counter
print(Counter(hex(t) for _,t,_ in hits))
for site,tgt,p in hits:
 if p in (1,8) and ((0x340000<=site<0x360000) or (0xA2000<=site<0xA3000) or (0x60000<=site<0x70000)):
  print("  site 0x%06X -> 0x%06X push=%s"%(site,tgt,p))
