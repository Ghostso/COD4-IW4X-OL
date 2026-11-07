import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_b83.txt","w",encoding="utf-8")
for rva,n,tag in [(0xB83B50,0x40,"0xB83B50"),
                  (0xB832E0,0x40,"0xB832E0"),
                  (0xB83370,0x30,"0xB83370"),
                  (0xB83390,0x30,"0xB83390"),
                  (0xB83A50,0x40,"0xB83A50"),
                  (0xB83B30,0x20,"0xB83B30"),
                  (0xB83B90,0x20,"0xB83B90"),
                  (0x6A9390,0x60,"0x6A9390")]:
    dump(img, rva, n, OUT, tag)
OUT.close()
print(open(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_data\out_b83.txt",encoding="utf-8").read())
print()
print("=== where is [session+0x628] written? scan 6A9xxx..6ADxxx ===")
for i in img.dis(0x6A9000,0x6AD000-0x6A9000):
    s=i.op_str.lower()
    if "+ 0x628]" in s: print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
