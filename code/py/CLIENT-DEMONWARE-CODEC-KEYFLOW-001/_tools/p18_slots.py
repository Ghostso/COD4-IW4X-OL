import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
vt=0xC5A31C
for k in range(16):
    v=im.rd(vt+4*k,4)
    print("  slot[%2d] = 0x%08X"%(k, int.from_bytes(v,"little")))
