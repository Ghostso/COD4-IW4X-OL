import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_6aa230.txt","w",encoding="utf-8")
dump(img, 0x6AA230, 0x140, OUT, "0x6AA230 (caller passes data0,data1)")
dump(img, 0x6AA320, 0x1E0, OUT, "0x6AA320")
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_6aa230.txt",encoding="utf-8").read())
