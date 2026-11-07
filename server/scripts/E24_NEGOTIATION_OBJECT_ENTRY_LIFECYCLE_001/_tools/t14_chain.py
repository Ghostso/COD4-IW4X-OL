import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img(); IB=img.IB
# find function start of 0x6AA470 by scanning back to 0xCC
j=0x6AA470
while j>0x1000 and img.d[img.off(j)-1]==0xcc: j-=1
print("start of func containing 6AA470:",hex(j))
for i in img.dis(j,0x40): print("  %06X %s %s"%(i.address-IB,i.mnemonic,i.op_str))
print()
print("0xAAB260 / 0xAAB310 boundaries:")
for s in (0x6AB260,0x6AB310):
    k=s
    while k>0x1000 and img.d[img.off(k)-1]!=0xcc: 
        if img.dis(k,1) and img.dis(k,1)[0].mnemonic=='ret': break
        k-=1
    print("  0x%06X prev-CC-scan -> 0x%06X"%(s,k))
print()
# callers of 0xAAB310 and 0xAAB260 and the phase1 func
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i] in (0xe8,0xe9):
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append((hex(va+i),hex(data[i])))
    return out
for nm,tv in [("0xAAB310",0xAAB310),("0xAAB260",0xAAB260),("phase1 fn 0xAAA4xx",IB+ (0x6AA470-0x1c0))]:
    print(nm, callers(tv))
