import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
print("=== 0x989230 (node accessor in pump) ===")
for i in img.dis(0x589230,0x10): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== 0x6AA830..0x6AA8A0 reprint (exact) ===")
for i in img.dis(0x6AA830,0x75): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== 0xB83370 / 0xB83390 (buffer space) reprint ===")
for i in img.dis(0x783370,0x35): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
