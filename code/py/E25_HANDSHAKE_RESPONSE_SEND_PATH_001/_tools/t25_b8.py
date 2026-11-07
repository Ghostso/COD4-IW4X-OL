import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# read the object at edi+0xB8 region in Dispatcher: the queue head. Also check field 0x628 and 0xB8-type in 6AA611-6AA620 (init)
print("=== 0x6AA5F0..0x6AA640 (init of b8/bc/c0) ===")
for i in img.dis(0x6AA5F0,0x60): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== who writes [edi+0xB8] (queue head type) - scan whole .text for 'mov [reg+0xb8],' ===")
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
import re
for i in range(len(data)-8):
    if data[i] in (0x89,0x8b) and data[i+2]==0xb8 and data[i+3]==0 and data[i+4]==0 and data[i+5]==0:
        r=va+i
        if 0x6A0000<=r<=0x6AD000 or 0xAA0000<=r<=0xAB0000:
            print("  %06X ctx=%s"%(r,data[i:i+8].hex()))
