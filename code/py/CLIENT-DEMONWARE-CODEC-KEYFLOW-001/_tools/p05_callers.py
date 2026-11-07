import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img(); IB=im.IB
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
d=im.d[rp:rp+rs]
for va,label in [(0xAA8D70,"codec_A"),(0xAA8BF0,"codec_B"),(0xAA9CE0,"expandKey"),(0xAA95C0,"hmacSha1"),(0xA881B0,"sha1")]:
    callers=[]
    for i in range(len(d)-5):
        if d[i]==0xe8:
            rel=struct.unpack_from("<i",d,i+1)[0]
            tgt=(IB+sva+i+5+rel)&0xffffffff
            if tgt==va: callers.append(IB+sva+i)
    # indirect FF15/FFD2 targeting the address via literal
    lits=[]
    pat=struct.pack("<I",va)
    j=d.find(pat)
    while j!=-1:
        lits.append(IB+sva+j); j=d.find(pat,j+1)
    print("%-10s %08X direct_callers=%d %s  literal_refs=%d %s"%(label,va,len(callers),[hex(c) for c in callers],len(lits),[hex(l) for l in lits[:10]]))
