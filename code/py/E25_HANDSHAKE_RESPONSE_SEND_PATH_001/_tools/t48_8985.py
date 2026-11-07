import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
b=img.rd(0x898560,0x60)
print("=== .rdata 0x898560..0x8985C0 ===")
for i in range(0,0x60,4):
    v=struct.unpack_from("<I",b,i)[0]
    print("  %08X = %08X sec=%s"%(0x898560+i,v,img.sec(v-IB) if 0x400000<=v<IB+img.pe.OPTIONAL_HEADER.SizeOfImage else None))
