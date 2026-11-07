import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
def d(va,n,tag):
    r=va-IB
    print("=== %s VA %08X RVA %06X sec=%s ==="%(tag,va,r,img.sec(r)))
    o=img.off(r)
    if o is None: print("  NO_RAW"); return
    for i in img.dis(r,n): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
d(0xDF16878,0x50,"0xDF16878 getter (.tvm0)")
d(0xB83A50,0x50,"0xB83A50 (socket holder init)")
d(0xB83B90,0x30,"0xB83B90 (socket close)")
print()
print("=== who writes session[+0xC4] object / where is socket stored ===")
for i in img.dis(0x6AA6E0,0x20): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
