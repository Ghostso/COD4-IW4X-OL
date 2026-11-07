import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for va,tag in [(0x48550D,"ref to +5F9 #1"),(0x9D1B48,"ref to +5F9 #2"),(0x99B40C,"ref to +60D #1"),(0x9DB779,"ref to +60D #2")]:
    print("="*70); print(tag, hex(va))
    for i in im.dis(va-0x20-0x400000, 0x50):
        print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
