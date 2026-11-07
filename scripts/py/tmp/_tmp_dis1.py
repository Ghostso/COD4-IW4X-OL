import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img(); IB=im.IB
for va,n,tag in [(0xAAB800,0x1000,"BDDATA/CLIENTCHAL xref region"),
                 (0xAAB600,0x400,"upstream")]:
    print("="*100); print(tag, hex(va))
    for i in im.dis(va-IB,n):
        print("%08X %-20s %s %s" % (i.address, bytes(i.bytes).hex(), i.mnemonic, i.op_str))
