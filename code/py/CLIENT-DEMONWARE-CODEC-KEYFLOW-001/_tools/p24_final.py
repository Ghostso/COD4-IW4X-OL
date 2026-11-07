import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
print("### outbound codecB call site 0xAAB03E-0xAAB046 (dir=0 = LOAD)")
for i in im.dis(0xAAB030-0x400000,0x28):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("### inbound codecA call site 0xAAACE3 (dir=0 = LOAD)")
for i in im.dis(0xAAACD4-0x400000,0x20):
    print("  %08X %-16s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("### AES provider construction 0xAAB941-0xAABA08")
for i in im.dis(0xAAB941-0x400000,0xD0):
    print("  %08X %-18s %s %s"%(i.address,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
