import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img()
print("=== 0xA888A0 subobject ctor: writes [ecx]=0xC5A3FC, [ecx+4]=arg ===")
print("=== vtable 0xC5A3FC ===")
import struct
b=img.rd(0xC5A3FC,0x20)
for i in range(0,0x20,4): print("   +%02X = %08X"%(i,struct.unpack_from('<I',b,i)[0]))
print()
print("=== 0x687BA0: what ecx is used at 0x687BCB? ===")
for i in img.dis(0x687BC4,0x20): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== 0xA888A0 body (ecx = this+0xC ?) ===")
for i in img.dis(0x6888A0,0x18): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
