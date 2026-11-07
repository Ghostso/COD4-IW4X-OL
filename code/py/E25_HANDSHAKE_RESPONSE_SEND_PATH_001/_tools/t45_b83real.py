import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def d(va,n,tag):
    r=va-IB
    print("=== %s VA %08X RVA %06X sec=%s ==="%(tag,va,r,img.sec(r)))
    o=img.off(r)
    if o is None: print("  NO_RAW"); return
    for i in img.dis(r, n): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
d(0xB83B50,0x60,"0xB83B50 (pump: insert into +0xC4)")
d(0xB832E0,0x50,"0xB832E0")
d(0xB83370,0x40,"0xB83370")
d(0xB83390,0x40,"0xB83390")
