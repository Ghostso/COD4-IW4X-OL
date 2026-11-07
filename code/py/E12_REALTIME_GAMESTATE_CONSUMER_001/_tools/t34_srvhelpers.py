# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=S.off(0xA0468)
from collections import Counter
c=Counter(); sites=[]
for ins in md.disasm(S.d[o:o+(0xA09B0-0xA0468)],S.IB+0xA0468):
    if ins.mnemonic=="call":
        for op in ins.operands:
            if op.type==1:
                t=(op.imm-S.IB)&0xffffffff
                c[t]+=1; sites.append((ins.address-S.IB,t))
print("call targets inside WriteConfigstrings:")
for t,n in c.most_common(): print("   0x%06X x%d"%(t,n))
print()
print("=== all call sites with preceding push ===")
insns=[]
o2,_=S.off(0xA0468)
for ins in md.disasm(S.d[o2:o2+(0xA09B0-0xA0468)],S.IB+0xA0468): insns.append(ins)
for i,ins in enumerate(insns):
    if ins.mnemonic=="call":
        for op in ins.operands:
            if op.type==1:
                t=(op.imm-S.IB)&0xffffffff
                ps=[x.op_str for x in insns[max(0,i-5):i] if x.mnemonic in ("push","mov") and ("esp + 4]" in x.op_str or x.mnemonic=="push")]
                print("   %06X -> 0x%06X  prev=%s"%(ins.address-S.IB,t,ps[-3:]))
