import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
for a in (0x6ABA4B,0x6ABA25,0x6AB97A,0x6AB9DA,0x6AB5C1,0x6AB4FF):
    o=img.off(a); b=img.d[o:o+5]
    if b[0]==0xe8:
        rel=struct.unpack_from("<i",b,1)[0]
        trva=(a+5+rel)&0xffffffff
        print("  call@%06X bytes=%s -> VA %08X RVA %06X sec=%s"%(a,b.hex(),IB+trva,trva,img.sec(trva)))
