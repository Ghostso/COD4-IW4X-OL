# -*- coding: utf-8 -*-
"""TASK-034: independently locate battle entry points in the LOCAL target via string xrefs."""
import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def va_of_str(off): return off+BASE
def find_str(s):
    i=d.find(s); return (i, i+BASE) if i>=0 else (None,None)
def xref_push(va):
    pat=b"\x68"+struct.pack("<I",va); out=[]; s=0
    while True:
        i=d.find(pat,s)
        if i<0: break
        out.append(i); s=i+1
    return out
def entry_back(off, back=0x600):
    for p in range(off,off-back,-1):
        if p<=0: break
        if d[p-1]==0xCC and (d[p:p+3] in (b"\x55\x8b\xec",b"\x6a\xff") or d[p:p+2]==b"\x8b\xff"):
            return p
    return None
print("== LOCAL battle command strings -> referencing code -> enclosing function ==")
print("%-22s %-12s %-10s %-12s %s" % ("string","VA","xref_off","xref_RVA","enclosing function entry RVA"))
for lab,s in [(b"getchallenge 0",b"getchallenge 0"),(b"challengeResponse",b"challengeResponse"),
              (b"connectResponse",b"connectResponse"),(b"gamestateupdate %d",b"gamestateupdate %d"),
              (b"heartbeat",b"heartbeat"),(b"cancelConnect",b"cancelConnect")]:
    off,va=find_str(s)
    if off is None: print("%-22s NOT FOUND" % lab.decode()); continue
    xs=xref_push(va)
    if not xs:
        # look for mov reg,imm
        xs=[]
        for op in (0xB8,0xB9,0xBA,0xBB,0xBE,0xBF):
            p=bytes([op])+struct.pack("<I",va); q=0
            while True:
                i=d.find(p,q)
                if i<0: break
                xs.append(i); q=i+1
    for x in xs[:3]:
        e=entry_back(x)
        print("%-22s %-12X %-10X %-12X %s" % (lab.decode(),va,x,x,("%X-RVA %X"%(e,e)) if e else "-"))
