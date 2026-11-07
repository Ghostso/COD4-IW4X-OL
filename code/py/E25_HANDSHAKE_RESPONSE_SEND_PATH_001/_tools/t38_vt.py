import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def vt(rva,label):
    b=img.bytes(rva,0x40)
    print("=== %s VA %08X RVA %06X sec=%s ==="%(label,IB+rva,rva,img.sec(rva)))
    if b is None: print("  NO_RAW"); return
    for i in range(0,0x40,4):
        v=struct.unpack_from("<I",b,i)[0]
        print("  +%02X = %08X sec=%s"%(i,v,img.sec(v-IB) if 0x400000<=v<IB+img.pe.OPTIONAL_HEADER.SizeOfImage else None))
for rva,l in [(0xC5B0E0-IB,"pair vtable"),(0xCBB D24-IB if False else 0x0,"")]:
    if rva: vt(rva,l)
vt(0x85B0E0,"pair vtable (VA 0xC5B0E0)")
vt(0x8BBD1C,"session vtable base? (VA 0xCBB D1C)")
