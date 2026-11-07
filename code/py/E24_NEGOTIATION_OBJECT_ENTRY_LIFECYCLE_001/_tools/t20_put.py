import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img()
for rva,n,tag in [(0x685B50,0x60,"0xA85B50 (put)"),(0x685490,0x60,"0xA85490 (field dispatch)"),(0x6A88400,0x50,"0xA88400")]:
    print("=== %s RVA %06X ==="%(tag,rva))
    for i in img.dis(rva,n): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
    print()
