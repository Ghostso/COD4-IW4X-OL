import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
out=open(r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001\_data\transcript_region.txt","w",encoding="utf-8")
for i in im.dis(0xAAB250-0x400000, 0x6B0):
    out.write("%08X %-18s %s %s\n"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
out.close()
print("ok")
