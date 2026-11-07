import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for a,n,tag in [(0x41DE60,0x90,"0x41DE90 ctx"),(0x41DF50,0x90,"0x41DF79 ctx")]:
    print("="*80); print(tag)
    for i in im.dis(a-0x400000,n):
        print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
