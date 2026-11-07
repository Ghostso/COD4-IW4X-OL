import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
print("0xC5BEB4 byte =", hex(im.rd(0xC5BEB4,1)[0]))
p=im.u32(0xC5BEB0); print("0xC5BEB0 ptr =", hex(p), "->", im.rd(p,32))
print()
print("### inbound decrypt call 0xAAB140-0xAAB160")
for i in im.dis(0xAAB140-0x400000,0x28):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("### outbound encrypt call 0xAAACB5-0xAAACD0")
for i in im.dis(0xAAACB5-0x400000,0x20):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
