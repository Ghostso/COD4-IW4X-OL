import sys, re
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
from capstone import *
im=Img(); IB=im.IB
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
data=im.d[rp:rp+rs]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
pat=re.compile(r"\[(e[a-z]{2}) \+ (0x[0-9a-f]+)\]")
lo,hi=0x5D0,0x640
hits=[]
for ins in md.disasm(data, IB+sva):
    m=pat.search(ins.op_str)
    if not m: continue
    try: disp=int(m.group(2),16)
    except Exception: continue
    if lo<=disp<=hi:
        hits.append((ins.address, disp, m.group(1), ins.mnemonic, ins.op_str))
print("total insn-level obj-field hits:",len(hits))
for a,d,r,mn,ops in hits:
    print("%08X disp=+%03X reg=%s  %s %s"%(a,d,r,mn,ops))
