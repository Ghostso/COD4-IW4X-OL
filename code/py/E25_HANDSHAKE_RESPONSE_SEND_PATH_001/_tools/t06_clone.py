import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_clone_pump.txt","w",encoding="utf-8")
for rva,n,tag in [(0x320E30,0x90,"0x320E30 clone 0x1C node (called by 6AA230)"),
                  (0x6A97E0,0x60,"0x6A97E0 make_pair"),
                  (0x6AA7B0,0x130,"0x6AA7B0 pump/queue")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_clone_pump.txt",encoding="utf-8").read())
