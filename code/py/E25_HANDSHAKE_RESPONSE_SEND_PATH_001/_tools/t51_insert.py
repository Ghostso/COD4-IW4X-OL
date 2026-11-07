import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
for rva,n,tag in [(0xB84E40,0x60,"0xB84E40 (insert into +0xC4)"),
                  (0xB84F60,0x40,"0xB84F60"),
                  (0x6A92A0-0x100,0x30,"pre 0x6A92A0 sync")]:
    print("=== %s RVA %06X ==="%(tag,rva))
    for i in img.dis(rva,n): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
    print()
