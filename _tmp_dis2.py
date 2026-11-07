import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for a,n,tag in [(0xAA9CE0,0x500,"0xAA9CE0 expandKey?"),
                (0xA881A0,0x300,"0xA881A0 secret producer?"),
                (0xAA8D70,0x300,"0xAA8D70"),
                (0xAA8BF0,0x300,"0xAA8BF0")]:
    print("="*100); print(tag, hex(a))
    for i in im.dis(a-0x400000,n):
        print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
