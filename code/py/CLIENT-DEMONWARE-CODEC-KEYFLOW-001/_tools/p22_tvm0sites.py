import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for va in (0xDE0FEB1,0xDFC3AE5):
    print("="*70); print("tvm0 site", hex(va), "sec=", im.sec(va-0x400000))
    for i in im.dis(va-0x30-0x400000, 0x60):
        print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
