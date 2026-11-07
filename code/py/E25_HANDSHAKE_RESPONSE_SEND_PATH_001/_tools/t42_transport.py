import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i]==0xe8:
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append(hex(va+i))
    return out
print("callers of 0x6A9680 (set +0x628 transport):", callers(IB+0x6A9680))
print("callers of 0x6A9690:", callers(IB+0x6A9690))
print()
print("=== disasm 0x6A9680-0x6A9700 (setter + its caller) ===")
for i in img.dis(0x6A9680,0x90): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
