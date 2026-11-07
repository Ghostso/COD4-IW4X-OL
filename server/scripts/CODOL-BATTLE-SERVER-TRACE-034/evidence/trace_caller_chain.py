# -*- coding: utf-8 -*-
"""TASK-034: trace caller chain of the delta-field dispatcher; hunt server-message opcode switch."""
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
print("== caller chain of delta dispatcher 0x5F830 ==")
for site in (0x208432,):
    e=entry_back(site)
    print("  call site RVA %X -> enclosing entry RVA %s" % (site,("%X"%e) if e else "NONE"))
# callers of that enclosing function
e1=entry_back(0x208432)
idx={}
for i in range(len(d)-5):
    if d[i]==0xE8:
        rel=struct.unpack_from("<i",d,i+1)[0]
        t=(i+5+rel)&0xffffffff
        idx.setdefault(t,[]).append(i)
if e1:
    print("  callers of RVA %X : %s" % (e1, ", ".join("%X"%x for x in idx.get(e1,[])[:12]) or "NONE"))
    e2=entry_back(idx[e1][0]) if idx.get(e1) else None
    if e2:
        print("    -> enclosing RVA %X ; its callers: %s" % (e2, ", ".join("%X"%x for x in idx.get(e2,[])[:12]) or "NONE"))
print()
print("== hunt 6-way opcode switch (server message 0..5) : jmp [reg*4+tbl] with 6 plausible targets ==")
hits=[]
for i in range(0x401000,0x900000-7):
    r=i-BASE
    if d[r]==0xFF and d[r+1]==0x24:
        sib=d[r+2]; disp=struct.unpack_from("<I",d,r+3)[0]
        if not (0x401000<=disp<0x900000): continue
        targets=[]
        ok=True
        for k in range(6):
            try: t=struct.unpack_from("<I",d,disp-BASE+k*4)[0]
            except Exception: ok=False; break
            if not (0x401000<=t<0x900000): ok=False; break
            targets.append(t)
        if ok: hits.append((i,disp,targets))
for va,disp,t in hits[:20]:
    print("  jmp@RVA %X table@RVA %X targets=%s" % (va-BASE,disp-BASE,["%X"%(x-BASE) for x in t]))
print("  total 6-target switches: %d" % len(hits))
