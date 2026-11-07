import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
print("=== writes to esi/ebx/edi in 0x6AB3DC..0x6ABAD2 ===")
for i in img.dis(0x6AB3DC, 0x6ABAD2-0x6AB3DC):
    s=i.op_str
    if i.mnemonic=="mov" and (s.startswith("esi,") or s.startswith("ebx,") or s.startswith("edi,")):
        print("  %06X %-22s %s %s"%(i.address-img.IB,bytes(i.bytes).hex(),i.mnemonic,s))
