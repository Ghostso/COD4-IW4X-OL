import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001\_tools")
from peh import *
img=Img()
print("=== 0x720E30 exact: find function start by scanning back over 0xCC ===")
j=0x720E30
while j>0x1000 and img.d[img.off(j)-1]==0xcc: j-=1
print("  boundary start:",hex(j))
for i in img.dis(j,0x60): print("   %06X %-20s %s %s"%(i.address-img.IB,bytes(i.bytes).hex(),i.mnemonic,i.op_str))
print()
print("=== 0x4DAB40 (called at 0x6ABA4B) ===")
for i in img.dis(0x4DAB40,0x60): print("   %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
