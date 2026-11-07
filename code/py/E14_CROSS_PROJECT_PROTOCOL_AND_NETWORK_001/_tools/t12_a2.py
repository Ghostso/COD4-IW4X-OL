import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
from capstone import *
from capstone.x86 import *
from collections import Counter
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=S.off(0xA0468)
insns=list(md.disasm(S.d[o:o+(0xA09B0-0xA0468)],S.IB+0xA0468))
ct=Counter()
for ins in insns:
    if ins.mnemonic=="call":
        for op in ins.operands:
            if op.type==X86_OP_IMM: ct[(op.imm-S.IB)&0xffffffff]+=1
print("call targets in WriteConfigstrings:")
for t,n in ct.most_common(): print("  0x%06X x%d"%(t,n))
