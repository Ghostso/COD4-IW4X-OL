import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for a in (0xAAC192,0xAAC2F0):
    print("="*80); print("around",hex(a))
    for i in im.dis(a-0x120-0x400000, 0x280):
        print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
