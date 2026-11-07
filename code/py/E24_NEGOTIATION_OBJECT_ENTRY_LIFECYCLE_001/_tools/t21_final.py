import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img()
print("=== func start containing 0x6AB2ED ===")
j=0x6AB2ED
while j>0x1000:
    if img.d[img.off(j)-1]==0xcc: break
    j-=1
print("  start RVA:",hex(j))
for i in img.dis(j,0x40): print("   %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== ACE1B0 use of arg3 ([ebp+0xC]) ===")
for i in img.dis(0x6CE1B0,0x9E):
    if "0x18]" in i.op_str or "ebp + 0xc]" in i.op_str: print("   %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== callers of the func containing 6AB2ED (VA) ===")
import struct
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
tva=img.IB+j
hits=[]
for i in range(len(data)-5):
    if data[i] in (0xe8,0xe9):
        rel=struct.unpack_from("<i",data,i+1)[0]
        if ((img.IB+va+i+5+rel)&0xffffffff)==tva: hits.append((hex(va+i),hex(data[i])))
print("  ",hits)
