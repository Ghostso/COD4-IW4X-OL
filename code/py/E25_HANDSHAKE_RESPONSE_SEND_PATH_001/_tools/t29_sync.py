import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# disassemble around 0x6AA60C..0x6AA650 with a sync offset: use 0x6AA60C but check bytes
print("bytes 0x6AA5F0..0x6AA650:")
o=img.off(0x6AA5F0)
print(img.d[o:o+0x64].hex())
print()
# The Intel bytes 89 9e b8 00 00 00 => mov [esi+0xb8], ebx. Find the true start by decoding from a known-good earlier int3 boundary.
# 0x6AA610 appears mid-instruction; find real 0xCC-terimated start:
j=0x6AA5F0
while j>0x1000:
    if img.d[img.off(j)-1]==0xcc: break
    j-=1
print("scanback start:",hex(j))
for i in img.dis(j,0x60): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
