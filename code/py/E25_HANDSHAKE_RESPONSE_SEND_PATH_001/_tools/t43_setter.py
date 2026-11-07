import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
print("=== 0x68EE20..0x68EE60 (setter call site 0x68EE41) ===")
for i in img.dis(0x68EE20,0x60): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== 0x68A010..0x68A060 (other setter call site) ===")
for i in img.dis(0x68A010,0x60): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
