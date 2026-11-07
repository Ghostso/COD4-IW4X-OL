import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def vt(va,label):
    b=img.rd(va,0x40)
    print("=== %s VA %08X sec=%s ==="%(label,va,img.sec(va-IB)))
    if b is None: print("  NO_RAW"); return
    for i in range(0,0x40,4):
        v=struct.unpack_from("<I",b,i)[0]
        print("  +%02X = %08X sec=%s"%(i,v,img.sec(v-IB) if 0x400000<=v<IB+img.pe.OPTIONAL_HEADER.SizeOfImage else None))
vt(0xC5B0E0,"pair vtable")
vt(0xCBBD1C,"node/session vtable")
vt(0xCBBD24,"clone vtable")
