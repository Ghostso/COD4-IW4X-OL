# -*- coding: utf-8 -*-
import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# xrefs to WriteConfigstrings / WriteGamestate and to WriteByte wrapper 0x99551
targets={0xA0468:"WriteConfigstrings",0xA21B8:"WriteGamestate",0x99551:"WriteByte",0x99566:"WriteShort"}
sec=S.pe.sections[0];o,_=S.off(sec.VirtualAddress);text=S.d[o:o+sec.SizeOfRawData];base=S.IB+sec.VirtualAddress
hits={t:[] for t in targets}
for ins in md.disasm(text,base):
 if ins.mnemonic in ('call','jmp'):
  for op in ins.operands:
   if op.type==1:
    rva=(op.imm-S.IB)&0xffffffff
    if rva in targets: hits[rva].append((ins.address-S.IB,ins.mnemonic))
for t,n in targets.items():
 print("=== %s 0x%X ==="%(n,t))
 for s,k in hits[t]: print("   0x%X %s"%(s,k))
