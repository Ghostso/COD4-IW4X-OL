import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
# confirm role assignment: slot2 = encrypt used at outbound with provider +0x5F0 (key data[40:56])
print("vtable[2] (encrypt) = %08X" % int.from_bytes(im.rd(0xC5A31C+8,4),"little"))
print("vtable[3] (decrypt) = %08X" % int.from_bytes(im.rd(0xC5A31C+12,4),"little"))
print("outbound call at 0xAAACBD uses [vt+8]  ->", int.from_bytes(im.rd(0xC5A31C+8,4),"little")==0xA87CF0)
print("inbound  call at 0xAAB14E uses [vt+0xC] ->", int.from_bytes(im.rd(0xC5A31C+12,4),"little")==0xA87D50)
