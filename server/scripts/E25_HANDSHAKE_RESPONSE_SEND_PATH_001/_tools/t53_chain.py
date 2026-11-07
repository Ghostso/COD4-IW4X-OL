import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva, lim=None):
    out=[]
    for i in range(len(data)-5):
        if data[i] in (0xe8,):
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append(hex(va+i))
    return out
print("callers of send-wrapper 0xB84E40:", callers(IB+0x784E40))
print("callers of recv-wrapper 0xB84F60:", callers(IB+0x784F60))
print()
# The pump calls 0xB83B50 (RVA 783B50) which calls 0xB84E40. So the pump -> 783B50 -> send!
print("=== so chain: 0x6AA7B0(pump) -> 0x783B50 -> 0x784E40(send) ===")
print()
# check 0x783B50 callers
print("callers of 0x783B50 sink:", callers(IB+0x783B50))
# find the function that owns 0x6A92A0 (the counter/stat consumer) - it had *no* send
