import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
# find a solid boundary: scan back from 0x6AA610 to a preceding 0xCC or ret, then disasm
def prev_cc_or_ret(rva):
    j=rva
    while j>0x1000:
        if img.d[img.off(j)-1]==0xcc: return j
        j-=1
    return rva
st=prev_cc_or_ret(0x6AA610)
print("boundary:",hex(st))
for i in img.dis(0x6AA610,0x1E0):
    print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
