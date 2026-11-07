import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img()
print("=== 0xA888A0 (called by ctor with push 0x10) ===")
for i in img.dis(0x6888A0,0x50): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== writes to [reg+0x14] inside vtable object family (687xxx..688xxx) ===")
import re
for i in img.dis(0x687BA0,0x300):
    if "+ 0x14]" in i.op_str and i.mnemonic in ("mov","lea"): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
