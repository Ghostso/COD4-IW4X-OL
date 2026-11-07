# -*- coding: utf-8 -*-
"""a20: for each socket-API call site, find enclosing function + nearest string refs."""
import sys, os, struct, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
def s(rva, ml=200):
    b=C.raw(rva,ml)
    if b is None: return None
    e=b.find(b"\x00"); return b[:e].decode("latin1","replace")

# build function-start list by scanning for int3 padding boundaries
pads=[]
i=0x1000
while i<0x8a7000:
    if C._img[i]==0xCC:
        j=i
        while j<0x8a7000 and C._img[j]==0xCC: j+=1
        if j-i>=2: pads.append(j)  # function starts right after padding
        i=j
    else: i+=1
starts=sorted(set(pads))
import bisect
def func_of(addr):
    k=bisect.bisect_right(starts,addr)-1
    return starts[k] if k>=0 else None

sites={}
def add(name, va):
    for i in range(0x1000,0x8a7000-6):
        if C._img[i]==0xFF and C._img[i+1] in (0x15,0x25):
            if struct.unpack_from("<I",C._img,i+2)[0]==va: sites.setdefault(name,[]).append(i)
for nm,va in [("recv",0xCA84E4),("recvfrom",0xCA851C),("select",0xCA84E8),
              ("send",0xCA84E0),("sendto",0xCA8518),("connect",0xCA84F0),
              ("socket",0xCA8548),("bind",0xCA8554),("listen",0xCA84FC),("accept",0xCA8500)]:
    add(nm,va)

# nearest string literal referenced within the enclosing function
def nearby_strings(fs, fe):
    out=[]
    for i in range(fs, min(fe,fs+0x6000)-5):
        op=C._img[i]; v=None
        if op==0x68: v=struct.unpack_from("<I",C._img,i+1)[0]
        elif op==0x8D and C._img[i+1] in (0x0D,0x05,0x15,0x0D): v=struct.unpack_from("<I",C._img,i+2)[0]
        if v and 0x8B0000<=v<0xE00000:
            st=s(v-IB,120)
            if st and len(st)>=5 and all(32<=ord(c)<127 for c in st[:5]):
                out.append(st)
    return out

for nm, addrs in sites.items():
    print("=== %s ==="%nm)
    for a in addrs:
        fs=func_of(a)
        # find end: next function start after a
        k=bisect.bisect_right(starts,a)
        fe=starts[k] if k<len(starts) else a+0x4000
        ss=nearby_strings(fs,fe) if fs else []
        print("  site 0x%08X  func 0x%08X..0x%08X  strs=%s"%(a, fs or 0, fe, ss[:4]))
