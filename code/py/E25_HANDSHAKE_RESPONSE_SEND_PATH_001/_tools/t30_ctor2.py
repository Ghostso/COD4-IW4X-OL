import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
for i in img.dis(0x6AA5C5,0x60): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
