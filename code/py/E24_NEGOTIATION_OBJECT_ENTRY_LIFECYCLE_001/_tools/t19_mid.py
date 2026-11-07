import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img()
for i in img.dis(0x6AC240,0x95):
    print("%06X %-22s %s %s"%(i.address-img.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
