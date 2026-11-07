import sys,struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img();d=im.d
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
sec=d[rp:rp+rs]
# find mov byte ptr [x+disp], 0xAB / 0x85 / 0x82 / 0x81 pairs
res=[]
for i in range(len(sec)-8):
    # c6 45 xx imm  (mov byte [ebp+disp8], imm)
    if sec[i]==0xc6 and sec[i+1]==0x45:
        imm=sec[i+3]
        if imm in (0xab,0x85,0x82,0x81,0x86):
            res.append((sva+i,imm))
    # c6 85 disp32 imm
    if sec[i]==0xc6 and sec[i+1]==0x85:
        imm=sec[i+6]
        if imm in (0xab,0x85,0x82,0x81,0x86):
            res.append((sva+i,imm))
from collections import Counter
print(Counter(v for _,v in res))
for a,v in res:
    if v in (0x85,0xab):
        print("RVA %06X VA %08X imm=%02X"%(a,0x400000+a,v))
