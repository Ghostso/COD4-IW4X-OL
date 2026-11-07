import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
# scan for disp32=0x628 in .text via opcode patterns (89/8b xx 28 06 00 00)
import re
print("=== byte-scan disp32=0x00000628 within 0x6A9000..0x6AD000 ===")
for i in range(0x6A9000-va, 0x6AD000-va):
    if data[i:i+4]==b"\x28\x06\x00\x00":
        r=va+i
        print("  approx %06X ctx=%s"%(r, data[i-3:i+6].hex()))
print()
print("=== disasm 0x589230 (called by pump) ===")
for i in img.dis(0x589230,0x50): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== disasm 0x77FD10 ===")
for i in img.dis(0x77FD10,0x50): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
