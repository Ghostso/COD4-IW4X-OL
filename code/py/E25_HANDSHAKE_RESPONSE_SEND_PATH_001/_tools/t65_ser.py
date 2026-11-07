import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
# find real boundary of function containing 0x4DAB40 (call target from 6ABA4B)
def start_by_cc(rva):
    j=rva
    while j>0x1000 and img.d[img.off(j)-1]!=0xcc: j-=1
    return j
# But 0x4DAB40 may be mid-function. Search backwards for prologue 55 8B EC
j=0x4DAB40
while j>0x1000:
    o=img.off(j)
    if img.d[o]==0x55 and img.d[o+1]==0x8b and img.d[o+2]==0xec: break
    j-=1
print("prologue found at RVA:",hex(j))
for i in img.dis(j,0x40): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("=== 0x6A81E5 (target of DECFC0E jmp) ===")
for i in img.dis(0x6A81E5,0x60): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
