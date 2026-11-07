import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img()
print("=== all 'mov dword ptr [reg + 0x14], ' in .text (byte pattern C7 4x 14 00 00 00) ===")
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
hits=[]
for i in range(len(data)-7):
    if data[i]==0xc7 and data[i+2]==0x14 and data[i+3]==0 and data[i+4]==0 and data[i+5]==0:
        hits.append(va+i)
print("  count:",len(hits))
for h in hits[:40]: print("   %06X"%h)
print()
print("=== writes to [ecx+0x14] or [esi+0x14] near 0x687xxx (the object ctor) ===")
for i in img.dis(0x687BA0,0x400):
    if "0x14]" in i.op_str and i.mnemonic in ("mov","lea"): print("   %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
