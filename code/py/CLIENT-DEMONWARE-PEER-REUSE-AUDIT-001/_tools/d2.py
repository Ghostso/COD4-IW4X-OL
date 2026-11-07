import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img(); IB=im.IB
consts = {"SHA1_H0":0x67452301,"SHA1_H1":0xEFCDAB89,"SHA1_H2":0x98BADCFE,"SHA1_H3":0x10325476,"SHA1_H4":0xC3D2E1F0,"K0":0x5A827999,"K1":0x6ED9EBA1,"K2":0x8F1BBCDC,"K3":0xCA62C1D6}
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
d=im.d[rp:rp+rs]
for name,v in consts.items():
    pat=struct.pack("<I",v); idx=[]; i=d.find(pat)
    while i!=-1 and len(idx)<40:
        idx.append(sva+i); i=d.find(pat,i+1)
    print("%-8s %08X hits=%d %s"%(name,v,len(idx),[hex(IB+a) for a in idx[:12]]))
for name,pat in (("ipad36x16",b"\x36"*16),("opad5cx16",b"\x5c"*16),("ipad36x64",b"\x36"*64),("opad5cx64",b"\x5c"*64)):
    idx=[];i=d.find(pat)
    while i!=-1 and len(idx)<20:
        idx.append(sva+i);i=d.find(pat,i+1)
    print(name,"hits",len(idx),[hex(IB+a) for a in idx[:10]])
