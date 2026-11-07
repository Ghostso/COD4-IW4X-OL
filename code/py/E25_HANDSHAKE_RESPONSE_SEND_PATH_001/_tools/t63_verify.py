import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# Final: verify the enqueue arg registers at 0x6AA2C7-0x6AA2D0 and the send call site bytes
print("=== enqueue call 0x6AA2D0 context ===")
for i in img.dis(0x6AA2B0,0x30): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== send chain bytes ===")
for a in (0x6AA88D,0x783B5E,0x784E5D):
    o=img.off(a); b=img.d[o:o+6]
    print("  %06X %s"%(a,b.hex()))
print()
# socket() triple at 0xB8495B
o=img.off(0x784950)
print("  socket setup bytes 0x784950..:", img.d[o:o+0x30].hex())
print("  => push 6;push 1;push 2 -> socket(AF_INET=2, SOCK_STREAM=1, IPPROTO_TCP=6)")
