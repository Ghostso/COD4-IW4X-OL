# -*- coding: utf-8 -*-
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
import pefile

# helper: FF15 target address
def tgt15(ins):
    op=ins.op_str
    m=re.search(r"\[(0x[0-9a-f]+)\]", op)
    return int(m.group(1),16) if m else None

ordmap={}
q=pefile.PE(r"C:\Windows\SysWOW64\ws2_32.dll", fast_load=False)
for e in q.DIRECTORY_ENTRY_EXPORT.symbols:
    if e.name: ordmap[e.ordinal]=e.name.decode()

def slot_info(r):
    v = rd32(r)
    if not v: return None
    if v & 0x80000000:
        od=v&0xffff; return ("ORD", od, ordmap.get(od,"ord:%d"%od))
    hn=read_hintname(v); return ("NAME", None, hn[1].decode("latin1") if hn else "?")

recv_slots=[]
for k in range(768):
    r=0xB02000+4*k; si=slot_info(r)
    if si and ("recv" in si[2].lower()):
        recv_slots.append((r,si))
print("receive-family IAT slots:")
for r,si in recv_slots: print("   0x%08X %s" % (IB+r, si))
ff=scan_ff15()
print()
print("FF15 call sites to receive-family slots:")
n=0
for i in ff:
    t=tgt15(i)
    for r,si in recv_slots:
        if t==IB+r:
            n+=1
            print("   0x%06X -> 0x%08X %s" % (i.address-IB, IB+r, si[2]))
print("total:",n)
