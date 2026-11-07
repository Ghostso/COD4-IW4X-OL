import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
print("### 0xAAA6D0-0xAAA710 (clear/reset of provider ptrs)")
for i in im.dis(0xAAA6D0-0x400000,0x48):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("### 0xAAA130-0xAAA180 (cleanup reads)")
for i in im.dis(0xAAA130-0x400000,0x50):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("### 0x417BF0-0x417C20 (is +0x5D0 float class?)")
for i in im.dis(0x417BF0-0x400000,0x30):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("### 0x41B1A0-0x41B230 (class check)")
for i in im.dis(0x41B1A0-0x400000,0x90):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
