import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
print("### outbound framing call site around 0xAAACE3")
for i in im.dis(0xAAAC90-0x400000, 0xC0):
    print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("### inbound HMAC key fetch around 0xAAB03E")
for i in im.dis(0xAAB030-0x400000, 0x60):
    print("%08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
