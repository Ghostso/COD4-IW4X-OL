import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
print("=== 6AA100..6AA1A0 (destructor clearing +5F0/+5F4) ===")
for i in img.dis(0x6AA100,0xA0):
    print("%06X %-18s %s %s"%(i.address-img.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("=== ACE080 tail / ACE1B0 table offsets ===")
for i in img.dis(0x6CE0CE,0x40):
    print("%06X %-18s %s %s"%(i.address-img.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
