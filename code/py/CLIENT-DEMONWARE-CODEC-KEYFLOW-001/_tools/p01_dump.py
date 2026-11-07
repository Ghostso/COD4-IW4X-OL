import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
def dump(va,n,path):
    with open(path,"w",encoding="utf-8") as f:
        for i in im.dis(va-0x400000,n):
            f.write("%08X %-20s %s %s\n"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
dump(0xAA8D70,0x180,r"CLIENT-DEMONWARE-CODEC-KEYFLOW-001\_data\codec_A_AA8D70.txt")
dump(0xAA8BF0,0x180,r"CLIENT-DEMONWARE-CODEC-KEYFLOW-001\_data\codec_B_AA8BF0.txt")
print("A bytes", len(im.dis(0xAA8D70-0x400000,0x180)))
print("B bytes", len(im.dis(0xAA8BF0-0x400000,0x180)))
