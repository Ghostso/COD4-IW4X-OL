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
for nm,tv in [("0x6A570 ctor",IB+0x6AA570),("0x6A9B20",IB+0x6A9B20),("0x6A9BE0",IB+0x6A9BE0)]:
    pass
# queue head at +0xb8 is used at 6AA830/6AA8CE (pump) and set at 6AA613 (ctor, =0)
# The insert 0xDF806F2 takes ecx = &[edi+0xb8]. So b8 is list-head of intrusive list.
# find all "lea ecx,[reg+0xb8]" sites
print("=== 'lea [reg+0xb8]' sites ===")
for i in img.dis(0x1000, 0x7AC900):
    s=i.op_str.lower()
    if i.mnemonic=="lea" and "+ 0xb8]" in s:
        print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== 'lea [reg+0x5f4]' / '[reg+0x5f4]' sites (context) ===")
for i in img.dis(0x1000, 0x7AC900):
    s=i.op_str.lower()
    if "+ 0x5f4]" in s:
        print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
