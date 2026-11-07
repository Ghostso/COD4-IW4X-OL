import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img(); IB=img.IB
for i in img.dis(0x6AA6E2,0x20): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
for i in img.dis(0x783B90,0x30): print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
# 0x783B50's ecx is &[session+0xC4] object; [ecx] = socket fd. So send(fd, buf, len)
print("0x783B50 semantics: send([ecx], [ebp+8]=buf, [ebp+0xC]=len) via 0x784E40(fd,buf,len)")
