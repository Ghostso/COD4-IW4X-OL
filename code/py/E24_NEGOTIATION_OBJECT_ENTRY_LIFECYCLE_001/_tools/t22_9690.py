import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img()
print("=== 0x6A9690 head ===")
for i in img.dis(0x6A9690,0x70): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== 0x6AB260 head (phase setter) ===")
for i in img.dis(0x6AB260,0x40): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
