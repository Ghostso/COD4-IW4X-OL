import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
def show(lo,hi,tag):
    print("="*70); print(tag)
    for i in img.dis(lo,hi-lo): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
show(0x6AA5F8,0x6AA670,"init region")
show(0x6AA60C,0x6AA628,"b8/bc/c0 init")
