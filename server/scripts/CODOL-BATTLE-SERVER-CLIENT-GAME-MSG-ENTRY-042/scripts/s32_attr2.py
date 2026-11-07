# -*- coding: utf-8 -*-
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
def get(off, ml=110):
    if off>=len(b): return None
    e=b.find(b"\0",off,off+ml)
    if e<0: e=off+ml
    if e-off<4: return None
    return b[off:e].decode("latin1")
def attr(lo,hi,path):
    hits=[]
    for ins in C.dis_range(lo,hi):
        rva=ins.address-C.IB
        for tok in ins.op_str.replace("["," ").replace("]"," ").replace(","," ").split():
            if tok.startswith("0x"):
                try: v=int(tok,16)
                except Exception: continue
                if 0x400000<=v<0x0e659000:
                    r=v-C.IB
                    if 0x8a8000<=r<0xa65000:
                        s=get(r)
                        if s: hits.append((rva,hex(r),s))
    seen=set(); uniq=[]
    for rva,tgt,s in hits:
        if (tgt,s) in seen: continue
        seen.add((tgt,s)); uniq.append((rva,tgt,s))
    o=io.open(os.path.join(C.EV,path),"w",encoding="utf-8",newline="")
    o.write("count=%d\n"%len(uniq))
    for rva,tgt,s in uniq: o.write("  %08x %-10s %s\n"%(rva,tgt,s[:120]))
    o.close()
    print("wrote",path,len(uniq))
attr(0x87a000,0x87f000,"modattr_netbuffer_region.txt")
attr(0x85e000,0x85f000,"modattr_85e000_85f000.txt")
attr(0x6d000,0x6f000,"modattr_6d000_6f000.txt")
