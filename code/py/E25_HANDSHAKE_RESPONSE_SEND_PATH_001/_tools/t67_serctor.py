import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
print("=== RVA 0xDAB40 (serializer ctor, arg=[ebp-0x17c]+6) ===")
for i in img.dis(0xDAB40,0x60): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== 0xDF6F97C field-append (used at 6ABAAA/6ABABB) ===")
for i in img.dis(0xDF6F97C-0x400000,0x50): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
