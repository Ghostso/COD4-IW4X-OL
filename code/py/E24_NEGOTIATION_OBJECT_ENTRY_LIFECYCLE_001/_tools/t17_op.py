import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
# byte-compares / stores of 0x81/0x83/0x84/0x85
pats={0x81:bytes([0x81]),0x83:bytes([0x83]),0x84:bytes([0x84]),0x85:bytes([0x85])}
print("=== 'C6 45 xx 81' style byte stores (mov byte [ebp-x], imm) for 0x81/83/84/85 ===")
for op in (0x81,0x83,0x84,0x85):
    hits=[]
    for i in range(len(data)-4):
        if data[i]==0xc6 and data[i+1]==0x45 and data[i+3]==op:
            hits.append(va+i)
    print("  mov byte [ebp-%02X], %02X : %s"%(0x100-(data[hits[0]-va+2] if hits else 0),op,[hex(h) for h in hits]))
print()
print("=== '3C 81' (cmp al,imm) for 0x81/83/84/85 ===")
for op in (0x81,0x83,0x84,0x85):
    hits=[va+i for i in range(len(data)-2) if data[i]==0x3c and data[i+1]==op]
    print("  cmp al,%02X : %s"%(op,[hex(h) for h in hits]))
print()
print("=== immediate DWORD/VAL 0x82, 0xAB, 0xD2 in 6AB310 body ===")
for val in (0x82,0xab,0xd2):
    hits=[va+i for i in range(len(data)-5) if data[i] in (0x68,0x6a) and struct.unpack_from("<I",data+b"\0\0\0",i+1)[0]==val]
    print("  push imm %02X : %s"%(val,[hex(h) for h in hits if 0x6ab000<=h<0x6abc00]))
print()
print("=== .data cipher table @0xD48F48 (VA) ===")
b=img.rd(0xD48F00,0xA0)
if b:
    for i in range(0,0xA0,4):
        print("  0x%08X = %08X"%(0xD48F00+i,struct.unpack_from("<I",b,i)[0]))
else:
    print("  NO RAW (outside .data raw)")
    print("  sec=",img.sec(0xD48F48-IB), "off=",img.off(0xD48F48-IB))
