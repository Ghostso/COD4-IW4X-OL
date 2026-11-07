import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
from capstone import *
S=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe")
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
o,_=S.off(0xA0468)
insns=list(md.disasm(S.d[o:o+(0xA09B0-0xA0468)],S.IB+0xA0468))
for i,ins in enumerate(insns):
    if ins.mnemonic=="call" and ins.op_str.startswith("0x"):
        t=int(ins.op_str,16)-S.IB
        if t in (0x99590,0xA0400,0x99566,0x99551):
            prev=["%s %s"%(x.mnemonic,x.op_str) for x in insns[max(0,i-5):i] if x.mnemonic in ("push","mov")]
            print("call 0x%06X @0x%06X prev: %s"%(t,ins.address-S.IB,prev[-3:]))
