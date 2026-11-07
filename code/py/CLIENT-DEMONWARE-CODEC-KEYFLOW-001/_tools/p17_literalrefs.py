import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
full=im.d
for va,lab in [(0xAA8D70,"codecA"),(0xAA8BF0,"codecB"),(0xAA9CE0,"expandKey")]:
    pat=struct.pack("<I",va); idx=[]; i=full.find(pat)
    while i!=-1: idx.append(i); i=full.find(pat,i+1)
    print("%s %08X  whole-image literal refs=%d"%(lab,va,len(idx)))
    for off in idx[:12]:
        sec=None
        for n,sv,vs,rp,rs,x in im.secs:
            if rp<=off<rp+rs: sec=n; break
        print("    off %08X sec=%s"%(off,sec))
