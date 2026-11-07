import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i] in (0xe8,):
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append(hex(va+i))
    return out
print("=== who writes session[+0x4B0] (transport source)? ===")
for i in img.dis(0x680000,0x3000): pass
# scan session-cluster 0x68A000..0x690000 and 0x6A9000..0x6AD000 for +0x4b0
for lo,hi in [(0x68A000,0x690000),(0x6A9000,0x6AD000)]:
    for i in img.dis(lo,hi-lo):
        s=i.op_str.lower()
        if "+ 0x4b0]" in s: print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== callers of pump 0x6AA7B0 and how transport is used ===")
print("  pump callers:", callers(IB+0x6AA7B0))
print()
print("=== 0x68EDC4 context (session ctor caller) ===")
for i in img.dis(0x68EDA0,0x60): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
