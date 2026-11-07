import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
for i in img.dis(0x6AB3DC,0x60): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== 0xDECFC0E (construct) ===")
for i in img.dis(0xDECFC0E-0x400000,0x40): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== 0x4DAB40 accurate (RVA 0x4DAB40) ===")
for i in img.dis(0x4DAB40,0x40): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
