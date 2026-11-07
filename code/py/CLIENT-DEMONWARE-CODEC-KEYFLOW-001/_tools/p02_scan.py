import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img(); IB=im.IB
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
d=im.d[rp:rp+rs]
targets=[0x5E0,0x5E8,0x5EC,0x5F0,0x5F4,0x5F8,0x5F9,0x5FC,0x600,0x604,0x608,0x60C,0x60D,0x610,0x614,0x618,0x61C,0x620,0x624,0x628]
hits={}
for t in targets:
    pat=struct.pack("<I",t)
    i=d.find(pat); c=[]
    while i!=-1:
        c.append(sva+i); i=d.find(pat,i+1)
    hits[t]=c
    print("disp32 %08X hits=%d %s"%(t,len(c),[hex(IB+a-3) for a in c[:20]]))
