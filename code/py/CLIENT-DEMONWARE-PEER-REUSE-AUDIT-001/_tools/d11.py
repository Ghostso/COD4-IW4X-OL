import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for va in (0x9CE310,0x7C6DA60,0x9BAFD0,0x9BA070,0x703A00,0x7039A0,0x711CD6,0x6FDAC4,0xA2E880,0xA2E790):
    b=im.rd(va,16); print("%08X %s %s"%(va,b.hex(" "), im.sec(va-0x400000)))
print()
# HMAC_Init_ex and SHA1 candidates
for a in (0xC73800,0xC73760,0xC737A0,0xC78040,0xC781C0,0xC73A60,0xC73AF0):
    print("%08X %s"%(a,im.rd(a,24).hex(" ")))
