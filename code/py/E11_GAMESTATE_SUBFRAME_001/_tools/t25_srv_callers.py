# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E11_GAMESTATE_SUBFRAME_001\_tools")
from pe_helper import PE
from sweep import sweep
from capstone import *
from capstone.x86 import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
sec=S.pe.sections[0]; o,_=S.off(sec.VirtualAddress)
text=S.d[o:o+sec.SizeOfRawData]; base=S.IB+sec.VirtualAddress
targets={0xA0468:"WriteConfigstrings",0xA21B8:"WriteGamestate",0x99551:"WriteByte",0x99566:"WriteShort",0x9949B:"WriteData"}
hits={k:[] for k in targets}
insns=list(sweep(md,text,base))
for ins in insns:
    if ins.mnemonic in ("call","jmp"):
        for op in ins.operands:
            if op.type==X86_OP_IMM:
                t=(op.imm-S.IB)&0xffffffff
                if t in targets: hits[t].append((ins.address-S.IB,ins.mnemonic))
for t,n in targets.items():
    print("=== %s 0x%X : %d refs ==="%(n,t,len(hits[t])))
    for s,k in hits[t]: print("    0x%06X %s"%(s,k))
