import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_queue.txt","w",encoding="utf-8")
# 0x720E30 (node clone), 0xAA97E0, 0xDF806F2 (.tvm0), 0xDF37227, 0xAAA7B0 (pump)
for rva,n,tag in [(0x720E30,0x80,"0x720E30 (copy node)"),
                  (0x6A97E0,0x60,"0xAA97E0 (make pair)"),
                  (0x6AA7B0,0xC0,"0xAAA7B0 (queue pump)"),
                  (0x6AA4B0,0x80,"0xAAA4B0"),
                  (0x6A96E0,0x80,"0xAA96E0")]:
    dump(img, rva, n, OUT, tag)
# .tvm0 helpers referenced by 6AA230
for va,n,tag in [(0xDF806F2,0x60,"0xDF806F2 queue insert (.tvm0)"),
                 (0xDF37227,0x40,"0xDF37227 node release (.tvm0)")]:
    dump(img, va-img.IB, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_queue.txt",encoding="utf-8").read())
