import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva, opc=(0xe8,)):
    out=[]
    for i in range(len(data)-5):
        if data[i] in opc:
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append(hex(va+i))
    return out
for nm,tv in [("0x775A22 send wrapper",0x775A22),("0x775AA2 sendto wrapper",0x775AA4),
              ("0x6A92A0 consumer",0x6A92A0),("0x6A95A0 stream-consume",0x6A95A0),
              ("0xAAA230",0xAAA230),("0xAAA7B0 pump",0xAAA7B0),
              ("0x6B4C94 sendto@6B4C94",0x6B4C94),("0x6028F0 send",0x6028F0)]:
    print("%-26s callers: %s"%(nm, callers(tv)))
print()
# who are the callers' functions? check 0x6B4DE0/0x784F60 (recv set from E-17)
print("=== E-17 recv wrappers for context ===")
for tv,nm in [(0x6B4DE0,"0x6B4DE0 recv"),(0x784F60,"0x784F60 recv")]:
    print("  %s callers:"%nm, callers(tv))
