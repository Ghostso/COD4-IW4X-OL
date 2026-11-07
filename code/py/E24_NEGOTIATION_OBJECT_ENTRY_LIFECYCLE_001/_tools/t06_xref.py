# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
IB=img.IB
n,va,vs,rp,rs,x=[s for s in img.secs if s[0]==".text"][0]
tdata=img.d[rp:rp+rs]
def rel_hits(target_va, opcodes=(0xe8,0xe9)):
    out=[]
    for i in range(len(tdata)-5):
        if tdata[i] in opcodes:
            rel=struct.unpack_from("<i",tdata,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==(target_va&0xffffffff):
                out.append((va+i, tdata[i]))
    return out
targets={'0x6AB310 (RVA)': (IB+0x6AB310),
         '0x6AAE70 (RVA)': (IB+0x6AAE70),
         '0x6AC0C0 (RVA)': (IB+0x6AC0C0),
         '0x6AC3D0 (RVA)': (IB+0x6AC3D0),
         '0x6ABBA0? ':[0]}
print("=== rel32 E8/E9 targeting ===")
for name,tv in [('0x6AB310',IB+0x6AB310),('0x6AAE70',IB+0x6AAE70),('0x6AC0C0',IB+0x6AC0C0),('0x6AC3D0',IB+0x6AC3D0),
                ('0x6AA230',IB+0x6AA230),('0x6AA770',IB+0x6AA770),('0xA87BA0',0xA87BA0),('0xA87D50',0xA87D50)]:
    h=rel_hits(tv)
    print("  %-10s VA %08X : %d ->"%(name,tv&0xffffffff,len(h)), [(hex(r),hex(o)) for r,o in h][:10])
print()
print("=== pointer-form scans ===")
for label,val in [('0x6AB310 VA',IB+0x6AB310),('0x6AB310 RVA',0x6AB310),
                  ('vt 0xC5A31C',0xC5A31C),('0xA87BA0 VA',0xA87BA0),('0xA87D50 VA',0xA87D50)]:
    pat=struct.pack("<I",val); print("  %-16s %08X : %d occurrences"%(label,val,img.d.count(pat)))
print()
# vtable 0xC5A31C slots
print("=== vtable 0xC5A31C ===")
b=img.rd(0xC5A31C,0x40)
for i in range(0,0x40,4):
    v=struct.unpack_from("<I",b,i)[0]
    secof = img.sec(v-IB) if 0x400000<=v<IB+img.pe.OPTIONAL_HEADER.SizeOfImage else None
    print("  slot+%02X = %08X  sec=%s"%(i,v,secof))
