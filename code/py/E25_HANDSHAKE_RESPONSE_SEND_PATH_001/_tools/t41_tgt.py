import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# correct the earlier confusion: 6AA8AA call target
def tgt(a):
    o=img.off(a); b=img.d[o:o+5]
    rel=struct.unpack_from("<i",b,1)[0]
    return (a+5+rel)&0xffffffff
for a in (0x6AA8AA,0x6AA8C1,0x6AA881):
    print("  call@%06X -> RVA %06X"%(a,tgt(a)))
print()
# What does the consumer 0x6A95A0 sub-call at 0x6a9627 do? dump
for i in img.dis(0x6A95C0,0x120): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
