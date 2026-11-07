import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def d(rva,n,tag):
    print("=== %s RVA %06X ==="%(tag,rva))
    for i in img.dis(rva,n): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
d(0x589230,0x10,"0x589230 getter [ecx+0x10]")
d(0x77FD10,0x8,"0x77FD10 getter [ecx+0x14]")
d(0x6C4070,0x8,"0x6C4070 getter [ecx+0xC]")
d(0x6AA830,0x75,"pump 0x6AA830 (parse + hand to transport)")
