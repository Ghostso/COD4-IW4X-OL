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
# find patterns: mov dword [esp+4], IMM  followed within 8 insns by call 0x499551 (WriteByte)
insns=list(sweep(md,text,base))
print("total insns",len(insns))
# index by address
addr2i={ins.address:i for i,ins in enumerate(insns)}
hits=[]
for i,ins in enumerate(insns):
    if ins.mnemonic=="call":
        for op in ins.operands:
            if op.type==X86_OP_IMM and (op.imm-S.IB)&0xffffffff==0x99551:
                # look back for mov dword [esp+4], imm
                val=None
                for j in range(i-1,max(-1,i-9),-1):
                    p=insns[j]
                    if p.mnemonic=="mov" and "esp + 4]" in p.op_str and p.operands and p.operands[-1].type==X86_OP_IMM:
                        val=p.operands[-1].imm; break
                    if p.mnemonic in ("call","ret"): break
                hits.append((ins.address-S.IB,val))
print("WriteByte call sites:",len(hits))
from collections import Counter
print("value histogram:",Counter(v for _,v in hits))
print()
for site,val in sorted(hits,key=lambda x:(x[1] if x[1] is not None else -1)):
    print("   site 0x%06X  WriteByte(%s)"%(site,val))
