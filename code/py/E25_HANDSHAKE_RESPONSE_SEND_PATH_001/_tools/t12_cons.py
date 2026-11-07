import sys, struct, pefile
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_consumers.txt","w",encoding="utf-8")
for rva,n,tag in [(0x6AA92A0,0xA0,"0x6AA92A0 consumer"),
                  (0x6AA95A0,0x90,"0x6AA95A0"),
                  (0x6AA9260,0x50,"0x6AA9260"),
                  (0x6AA9B20,0x80,"0x6AA9B20"),
                  (0xAC4070,0x60,"0xAC4070"),
                  (0xB83B50,0x40,"0xB83B50"),
                  (0xB83B90,0x40,"0xB83B90")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_consumers.txt",encoding="utf-8").read())
