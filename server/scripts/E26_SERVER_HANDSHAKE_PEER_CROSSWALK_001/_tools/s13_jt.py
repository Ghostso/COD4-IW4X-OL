import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S); IB=im.IB
print("=== jump table at VA 0x7B37A0 (5 entries) ===")
for k in range(6):
    v=im.u32(0x7B37A0+k*4-IB)
    print("  clc[%d] VA=0x7B37A0+%d -> %08X sec=%s"%(k,k*4,v,im.sec(v-IB) if v else None))
print()
print("=== related tables 0x7B3800 / 0x7B37xx ===")
for va in (0x7B3800,0x7B3780,0x7B3772,0x7B3762,0x7B3720,0x7B36c8):
    b=im.bytes(va-IB,0x18)
    print("  0x%08X: %s"%(va,b.hex() if b else None))
