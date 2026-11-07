import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# vtable at 0x898588 / 0x898590 from E-18
for va in (0x898588,0x898590):
    b=img.rd(va,0x40)
    print("=== vtable VA %08X ==="%va)
    if b is None: print("  NO_RAW"); continue
    for i in range(0,0x40,4):
        v=struct.unpack_from("<I",b,i)[0]
        print("  +%02X = %08X sec=%s"%(i,v,img.sec(v-IB) if 0x400000<=v<0x100000000 else None))
