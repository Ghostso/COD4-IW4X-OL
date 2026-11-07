import sys,struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
vt=0xC5A31C
print("provider vtable at %08X:"%vt)
for k in range(8):
    p=im.u32(vt+4*k)
    print("  [%d] %08X"%(k, p if p else 0))
print()
for m in (0xACE080,0xACE180,0xACE1B0):
    print("---- method %08X"%m)
    for i in im.dis(m-0x400000, 0x70):
        print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
