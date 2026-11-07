import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for i in im.dis(0xA87830-0x400000, 0x72):
    print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
# A88130 ctor and DEF75C68
for a,n in ((0xA88130,0x70),(0xDF75C68,0x90)):
    print("---- %08X"%a)
    for i in im.dis(a-0x400000, n):
        print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
