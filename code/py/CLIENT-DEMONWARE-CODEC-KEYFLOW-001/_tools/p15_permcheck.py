import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001\_tools")
from peh import Img
im=Img()
print("codec_B perm-table region 0xAA8C8C..0xAA8CBC:")
b=im.rd(0xAA8C8C,0x34)
print(b.hex(" "))
# decode as dwords
import struct
for k in range(0,len(b)-3,4):
    print("   +%02X  %s"%(k, struct.unpack_from("<I",b,k)[0]))
print()
print("codec_A perm-table region 0xAA8E0F..0xAA8E40:")
b=im.rd(0xAA8E0F,0x34); print(b.hex(" "))
for k in range(0,len(b)-3,4):
    print("   +%02X  %s"%(k, struct.unpack_from("<I",b,k)[0]))
