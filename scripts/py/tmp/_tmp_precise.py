import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
print("bytes @0xAAB8BC:", im.rd(0xAAB8BC,16).hex(" "))
print("bytes @0xAAB904:", im.rd(0xAAB904,16).hex(" "))
print("CLIENTCHAL raw  :", im.rd(0xC5B144,16))
# find function start: scan backwards for 55 8B EC  or 55 8B EC
start=None
for a in range(0xAAB8C5,0xAAA000,-1):
    if im.rd(a,3)==b"\x55\x8b\xec":
        start=a; break
print("func start candidate", hex(start))
