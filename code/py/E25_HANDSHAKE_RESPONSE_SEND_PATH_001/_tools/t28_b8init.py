import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
print("=== 0x6AA630..0x6AA660 (b8/bc/c0 init) ===")
for i in img.dis(0x6AA62E,0x40): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
# find where +0xb8 is set to a real container: look for mov [reg+0xb8], reg with reg from alloc
print("=== all [reg+0xB8] with 'mov' in whole .text (C7-style and 89-style) ===")
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
for i in range(len(data)-10):
    b=data[i:i+10]
    # 89 9E/8E/BE/86 xx b8 00 00 00  => mov [esi/ecx/edi/eax+0xb8], ebx/ecx/edi
    if b[0] in (0x89,0x8b) and b[1] in (0x86,0x96,0x9e,0x8e,0xbe,0x87,0x97,0x9f,0x8f,0xbf) and b[2]==0xb8 and b[3:6]==b"\x00\x00\x00":
        r=va+i
        print("  %06X %s"%(r,b[:10].hex()))
