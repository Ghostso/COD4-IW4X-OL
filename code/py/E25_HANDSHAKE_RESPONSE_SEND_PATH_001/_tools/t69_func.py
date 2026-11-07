import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
print("=== 0x6AAA10 start + does it write 5cc? ===")
for i in img.dis(0x6AAA10,0x60): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== 5cc refs in 0x6AAA10..0x6AAE60 ===")
for i in img.dis(0x6AAA10,0x6AAE60-0x6AAA10):
    if "0x5cc" in i.op_str.lower(): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i] in (0xe8,0xe9):
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append(hex(va+i))
    return out
print("callers of 0x6AAA10:", callers(IB+0x6AAA10))
print("callers of 0x6AAA320:", callers(IB+0x6AAA320))
