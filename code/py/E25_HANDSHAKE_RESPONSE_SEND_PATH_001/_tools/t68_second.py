import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# find function start containing 0x6AADE6 by locating prologue
j=0x6AADE6
while j>0x1000:
    o=img.off(j)
    if img.d[o]==0x55 and img.d[o+1]==0x8b and img.d[o+2]==0xec: break
    j-=1
print("prologue at:",hex(j))
for i in img.dis(j,0x30): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== 0x6AADC0..0x6AADF0 ===")
for i in img.dis(0x6AADC0,0x40): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i]==0xe8:
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append(hex(va+i))
    return out
print("callers of that function:", callers(IB+j))
