import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
C=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
im=Img(C); IB=im.IB
print("=== CLIENT 0x60DD60..0x60DDF0 ===")
for i in im.dis(0x60DD60,0x90): print("  %06X %-20s %s %s"%(i.address-IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
# table at VA 0xA0DDF4? disp from bytes: ff 24 85 ecdda000 -> VA 0xA0DDEC ; ff 24 85 f4dda000 -> 0xA0DDF4
for va in (0xA0DDEC,0xA0DDF4,0xA0DE00):
    print("  table VA %08X:"%va, [hex(im.u32(va-IB+k*4)) for k in range(5)])
