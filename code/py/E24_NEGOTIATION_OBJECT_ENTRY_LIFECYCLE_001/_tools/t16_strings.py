import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img()
b=img.rd(0xC5B120,0x60)
print("raw 0xC5B120..0xC5B180:")
print(b.hex())
print()
import re
for m in re.finditer(rb"[ -~]{3,}", b):
    print("  VA %08X len=%d : %r"%(0xC5B120+m.start(), len(m.group()), m.group().decode()))
print()
# also the key-builder 0xAA9CE0
print("=== 0xAA9CE0 (key/value collect) ===")
for i in img.dis(0x6A9CE0,0x90): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
