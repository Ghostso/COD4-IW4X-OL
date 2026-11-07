import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
print("=== 0x7759E0..0x775A50 (send/recv wrappers) ===")
for i in img.dis(0x7759E0,0x70):
    print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== 0x775AF0..0x775B80 (ctor?) ===")
for i in img.dis(0x775AF0,0x90):
    print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
