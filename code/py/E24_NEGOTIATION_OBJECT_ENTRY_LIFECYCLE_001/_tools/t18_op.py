import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
print("=== mov byte [ebp-d], imm8 for 0x81/83/84/85 ===")
for op in (0x81,0x83,0x84,0x85):
    hits=[va+i for i in range(len(data)-4) if data[i]==0xc6 and data[i+1] in (0x45,0x85) and data[i+3]==op]
    print("  %02X : %s"%(op,[hex(h) for h in hits]))
print()
print("=== cmp al,imm8 (3C) for 0x81/83/84/85 ===")
for op in (0x81,0x83,0x84,0x85):
    hits=[va+i for i in range(len(data)-2) if data[i]==0x3c and data[i+1]==op]
    print("  %02X : %s"%(op,[hex(h) for h in hits]))
print()
print("=== push imm32 0xD2 / 0xAB / 0x82 inside 6AB000..6ABC00 ===")
for val in (0xd2,0xab,0x82):
    hits=[]
    for i in range(0x6AB000-va, 0x6ABC00-va):
        if data[i]==0x68 and struct.unpack_from("<I",data,i+1)[0]==val:
            hits.append(hex(va+i))
    print("  push %02X : %s"%(val,hits))
print()
print("=== .data @0xD48F00 ===")
r=0xD48F00-IB
print("  sec:",img.sec(r),"off:",img.off(r))
b=img.bytes(r,0x60)
print("  raw:",b.hex() if b else None)
