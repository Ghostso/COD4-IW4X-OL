import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for i in im.dis(0xA881A0-0x400000, 0x100):
    print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
# resolve indirect targets used by A881B0
for a in (0xACC060,0xACDF00,0xACBE90):
    print("---- %08X"%a)
    for i in im.dis(a-0x400000, 0x60):
        print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
