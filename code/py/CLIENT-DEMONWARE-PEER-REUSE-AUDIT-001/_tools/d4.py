import sys,struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img(); IB=im.IB
# find xrefs to strings
strs={0xC5B0EC:"HMAC mismatch",0xC5B110:"Bad recv counter",0xC5B120:"Bad frame/payload size",0xC5B13C:"BDDATA",0xC5B144:"CLIENTCHAL"}
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
d=im.d[rp:rp+rs]
for va,name in strs.items():
    pat=struct.pack("<I",va); hits=[]; i=d.find(pat)
    while i!=-1:
        hits.append(IB+sva+i); i=d.find(pat,i+1)
    print("%-22s VA %08X xrefs %d: %s"%(name,va,len(hits),[hex(h) for h in hits]))
# init/ctor detection: find prologues referencing these call targets
for f in (0xAA8D70,0xAA8BF0,0xA881A0):
    print("---",hex(f),"first bytes",im.rd(f,20).hex(" "))
