import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_send_sites.txt","w",encoding="utf-8")
for rva,n,tag in [(0x6028B0,0x80,"send@6028F0"),
                  (0x76D630,0x70,"send@76D664"),
                  (0x7759E0,0x120,"send@775A22 / sendto@775AA4 (wsock wrapper)"),
                  (0x784E30,0x70,"send@784E5F"),
                  (0x787FC0,0x60,"send@787FE5"),
                  (0x6B4C60,0x60,"sendto@6B4C94"),
                  (0x0DFAB0,0x60,"sendto@0DFADD"),
                  (0x1B09C0,0x60,"sendto@1B09F1")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_send_sites.txt",encoding="utf-8").read())
