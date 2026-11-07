import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im = Img()
print("ImageBase", hex(im.IB), "SizeOfImage", hex(im.pe.OPTIONAL_HEADER.SizeOfImage))
for s in im.secs:
    print("  %-8s RVA %08X VA %08X VS %08X x=%s" % (s[0], s[1], im.IB+s[1], s[2], s[5]))
