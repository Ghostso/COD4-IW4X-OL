import struct, sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img();IB=im.IB
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]; d=im.d[rp:rp+rs]
for t in (0x5F9,0x60D,0x5F8,0x60C):
    pat=struct.pack("<I",t); c=[]; i=d.find(pat)
    while i!=-1: c.append(IB+sva+i); i=d.find(pat,i+1)
    print("  %X refs=%d %s"%(t,len(c),[hex(z) for z in c]))
