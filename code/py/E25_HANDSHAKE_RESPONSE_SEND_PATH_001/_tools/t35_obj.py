import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_obj.txt","w",encoding="utf-8")
for rva,n,tag in [(0x6A8D70,0x80,"0xAA8D70"),
                  (0x6A8BF0,0x80,"0xAA8BF0"),
                  (0x6A9B20,0x80,"0xAA9B20"),
                  (0x6AA0F0,0x60,"0xAAA0F0 (dtor)"),
                  (0x6AA9100,0x60,"0xAAA9100")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_obj.txt",encoding="utf-8").read())
