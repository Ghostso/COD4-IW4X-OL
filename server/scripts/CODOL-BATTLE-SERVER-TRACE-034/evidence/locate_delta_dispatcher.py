# -*- coding: utf-8 -*-
"""TASK-034: locate the local delta-field dispatcher's callers and the message parser family."""
import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def entry_back(r, back=0x4000):
    for p in range(r,r-back,-1):
        if p<=0: break
        if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff"):
            return p
    return None
print("== enclosing entries for the two type dispatchers ==")
for site in (0x5F89B,0x601A4):
    e=entry_back(site)
    print("  site RVA %X -> entry RVA %s" % (site,("%X"%e) if e else "NONE"))
print()
# Direct callers of candidate entries
print("== direct callers (E8 rel32) ==")
targets=[0x5F830,0x5FA70,0x5F730,0x5FA00,0x5F900]
idx={}
for i in range(len(d)-5):
    if d[i]==0xE8:
        rel=struct.unpack_from("<i",d,i+1)[0]
        t=(i+5+rel)&0xffffffff
        idx.setdefault(t,[]).append(i)
for t in targets:
    print("  entry RVA %X : %s" % (t, ", ".join("%X"%x for x in idx.get(t,[])[:12]) or "NONE"))
print()
print("== entry candidates in 0x5F700..0x60300 ==")
c=[p for p in range(0x5F700,0x60300) if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff")]
print("  " + " ".join("%X"%x for x in c))
