import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for a,n,tag in [(0xAA95C0,0x220,"0xAA95C0 (HMAC-SHA1?)"),
                (0xA88130,0x80,"0xA88130"),
                (0xA881A0,0x60,"0xA881A0"),
                (0xA881B0,0x140,"0xA881B0 (frame reader?)")]:
    print("="*90); print(tag,hex(a))
    for i in im.dis(a-0x400000,n):
        print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
