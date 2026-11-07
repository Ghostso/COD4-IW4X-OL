import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# scan .text for disp 0xB8/0xBC/0xC0 refs in the session range 0x6A9xxx-0x6ACxxx
import re
print("=== refs to [reg+0xB8]/[reg+0xBC]/[reg+0xC0] in 0x6A9000..0x6AD000 ===")
for i in img.dis(0x6A9000, 0x6AD000-0x6A9000):
    s=i.op_str.lower()
    if "+ 0xb8]" in s or "+ 0xbc]" in s or "+ 0xc0]" in s:
        print("  %06X %-6s %s"%(i.address-IB,i.mnemonic,i.op_str))
