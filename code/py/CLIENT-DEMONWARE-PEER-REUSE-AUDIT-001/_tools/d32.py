import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
# linear sweep from a valid boundary (0xAAB3C6) to catch all appends
for i in im.dis(0xAAB3C6-0x400000, 0x1A6):
    print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
