import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for m,tag in ((0xA87CF0,"slot2"),(0xA87D50,"slot3"),(0xA87FF0,"slot4"),(0xA87F20,"slot6")):
    print("="*70); print(tag, hex(m))
    for i in im.dis(m-0x400000,0x58):
        print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
