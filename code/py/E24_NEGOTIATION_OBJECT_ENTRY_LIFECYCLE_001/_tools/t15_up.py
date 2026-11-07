import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img=Img(); IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
data=img.d[rp:rp+rs]
def callers(tva):
    out=[]
    for i in range(len(data)-5):
        if data[i] in (0xe8,0xe9):
            rel=struct.unpack_from("<i",data,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==tva: out.append((hex(va+i),hex(data[i])))
    return out
for nm,tv in [("0x6AA320",IB+0x6AA320),("0x6AA440?",IB+0x6AA440),("0x6AA230",IB+0x6AA230),
              ("0xAAB310",0xAAB310),("0xAAB260",0xAAB260),("0xAAC0C0",0xAAC0C0),
              ("0x6A1540 (phase setter)",IB+0x6A1540)]:
    print("%-26s %s"%(nm,callers(tv)))
print()
# who writes [esi+0x5f4] or +0x5f0 besides 6AB310?
print("=== immediate 0x81/0x83/0x84/0x85 constants in .rdata strings near 0xC5B1xx ===")
for va in (0xC5B124,0xC5B110,0xC5B0FC,0xC5B0EC,0xC5B13C,0xC5B144,0xC5BEB0):
    b=img.rd(va,32)
    s=b.split(b"\0")[0].decode("latin1") if b else None
    print("  VA %08X: %r"%(va,s))
