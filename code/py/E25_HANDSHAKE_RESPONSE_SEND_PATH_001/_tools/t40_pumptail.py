import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
print("=== pump: after 0x6AA8C1 .. 0x6AAA20 ===")
for i in img.dis(0x6AA8C1,0x160): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
