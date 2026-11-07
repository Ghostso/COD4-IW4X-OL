import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_consumers2.txt","w",encoding="utf-8")
for rva,n,tag in [(0x6A92A0,0xB0,"0x6A92A0 (pump: process one node)"),
                  (0x6A95A0,0x90,"0x6A95A0"),
                  (0x589230,0x60,"0x589230"),
                  (0x6C4070,0x60,"0x6C4070"),
                  (0x7832E0,0x40,"0x7832E0"),
                  (0x783B30,0x40,"0x783B30"),
                  (0x783B50,0x40,"0x783B50"),
                  (0x783370,0x30,"0x783370"),
                  (0x783390,0x30,"0x783390"),
                  (0x685280,0x40,"0x685280"),
                  (0x685210,0x40,"0x685210")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_consumers2.txt",encoding="utf-8").read())
