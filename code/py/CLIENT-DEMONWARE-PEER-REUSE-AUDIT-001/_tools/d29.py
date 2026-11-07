import sys,struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img();IB=im.IB;d=im.d
n,sva,vs,rp,rs,x=[s for s in im.secs if s[0]=='.text'][0]
sec=d[rp:rp+rs]
# all rel32 call targets -> find callers of KDF anchors
for va,label in [(0xAA9CE0,"expandKey"),(0xAA95C0,"HmacSha1Out"),(0xA881B0,"Sha1Out"),(0xAAB310,"0x82 handler/KDF"),(0xAAAE70,"recv0x85 handler"),(0xAAA710,"dispatcher"),(0xAAAB40,"send frame builder")]:
    callers=[]
    for i in range(len(sec)-5):
        if sec[i]==0xe8:
            rel=struct.unpack_from("<i",sec,i+1)[0]
            tgt=(IB+sva+i+5+rel)&0xffffffff
            if tgt==va: callers.append(IB+sva+i)
    print("%-20s %08X callers=%d %s"%(label,va,len(callers),[hex(c) for c in callers[:20]]))
