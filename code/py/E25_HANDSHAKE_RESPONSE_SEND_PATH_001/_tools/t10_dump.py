import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_6ab310.txt","w",encoding="utf-8")
dump(img, 0x6AB310, 0x880, OUT, "0x6AB310 full (extended)")
OUT.close()
print("lines:", sum(1 for _ in open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_6ab310.txt",encoding="utf-8")))
# show region 6AB420..6AB4C0 (builder creation) and 6AB9F0..6ABA60
for lo,hi in [(0x6AB420,0x6AB4C4)]:
    for i in img.dis(lo,hi-lo):
        print("%06X %-22s %s %s"%(i.address-img.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
