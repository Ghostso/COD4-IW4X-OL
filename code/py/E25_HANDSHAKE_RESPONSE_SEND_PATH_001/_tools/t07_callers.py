import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# callers of 0x6AA230
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva, opc=(0xe8,0xe9)):
    out=[]
    for i in range(len(data)-5):
        if data[i] in opc:
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append((hex(va+i),hex(data[i])))
    return out
for nm,tv in [("0x6AA230",IB+0x6AA230),("0x6AA7B0",IB+0x6AA7B0),("0x320E30 clone",0x720E30),("0x6A97E0 pair",0x6A97E0),("0xAAA4B0",IB+0x6AA4B0)]:
    print("%-16s %s"%(nm,callers(tv)))
print()
# IAT: what is at 0xBae110/0xBae114 (used as refcount inc/dec)
print("=== IAT-ish 0xBAE110 / 0xBAE114 ===")
for va in (0xBAE110,0xBAE114):
    print("  %08X dword=%08X"%(va,img.u32(va-IB) or 0))
