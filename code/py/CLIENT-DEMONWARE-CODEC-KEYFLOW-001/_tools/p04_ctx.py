import sys, re
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
from capstone import *
im=Img(); IB=im.IB
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
data=im.d[rp:rp+rs]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
# Find every instruction in .text whose op_str references a disp in the key-field window,
# and print a +/- 12 instruction window context around those in the KDF/85 region.
want=re.compile(r"\+ (0x5f0|0x5f4|0x5f9|0x5e0|0x5e8|0x60d|0x604|0x608|0x60c|0x620|0x624)\b", re.I)
stream=list(md.disasm(data, IB+sva))
idx=[i for i,ins in enumerate(stream) if want.search(ins.op_str)]
print("matched instructions:",len(idx))
seen=set()
for i in idx:
    for j in range(max(0,i-8), min(len(stream), i+9)):
        if j in seen: continue
        seen.add(j)
        ins=stream[j]
        print("%08X %-20s %s %s"%(ins.address, bytes(ins.bytes).hex(), ins.mnemonic, ins.op_str))
    print("-"*80)
