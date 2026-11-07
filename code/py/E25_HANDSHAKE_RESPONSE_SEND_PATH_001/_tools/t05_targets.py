import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def d(va,n):
    o=img.off(va-IB)
    if o is None: print("  NO_RAW VA %08X RVA %06X sec=%s"%(va,va-IB,img.sec(va-IB))); return
    for i in img.dis(va-IB,n):
        print("  %06X %-20s %s %s"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print("ImageBase",hex(IB))
# verify 6AA230 call targets by explicit rel32
import struct
print("\n=== explicit rel32 targets inside 0x6AA230 ===")
for a in (0x6AA25C,0x6AA27B,0x6AA2B6,0x6AA2D0,0x6AA2D7,0x6AA2E3):
    o=img.off(a); b=img.d[o:o+5]
    if b[0]==0xe8:
        rel=struct.unpack_from("<i",b,1)[0]
        print("  caller RVA %06X -> target VA %08X target RVA %06X sec=%s"%(
            a, (IB+a+5+rel)&0xffffffff, (a+5+rel)&0xffffffff, img.sec((a+5+rel)&0xffffffff)))
