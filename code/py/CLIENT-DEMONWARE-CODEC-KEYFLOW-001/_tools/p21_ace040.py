import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
for a,n,tag in [(0xACE040,0xA0,"0xACE040"),(0xE00F7FB,0x80,"0xE00F7FB (tvm0)"),(0xDFCE62D,0x80,"0xDFCE62D (tvm0)")]:
    print("="*80); print(tag)
    ins=list(im.dis(a-0x400000,n))
    if not ins: print("  <no raw / unreadable>")
    for i in ins: print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
