import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
for rva,n,tag in [(0x6A1540,0x60,"0x6A1540 (phase=eax writer)"),
                  (0x687DA0,0x30,"0xA87DA0")]:
    for i in img.dis(rva,n):
        print("%06X %-18s %s %s"%(i.address-img.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
    print()
