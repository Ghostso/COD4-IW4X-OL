import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
for rva,n,tag in [(0x784E40,0x60,"0xB84E40 VA->RVA 0x784E40"),
                  (0x784F60,0x40,"0xB84F60 VA->RVA 0x784F60"),
                  (0x6A91A0,0x120,"0x6A91A0..0x6A92C0")]:
    print("=== %s ==="%tag)
    for i in img.dis(rva,n): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
    print()
