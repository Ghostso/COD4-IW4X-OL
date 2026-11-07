import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
def sb(rva):
    j=rva
    while j>0x1000:
        if img.d[img.off(j)-1]==0xcc: return j
        j-=1
    return rva
st=sb(0x6AADE6)
print("func start of second enqueue:",hex(st))
for i in img.dis(st, 0x6AAE70-st): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
