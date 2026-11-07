# -*- coding: utf-8 -*-
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
def get(off, ml=100):
    if off>=len(b): return None
    e=b.find(b"\0",off,off+ml)
    if e<0: e=off+ml
    if e-off<4: return None
    return b[off:e].decode("latin1")
hits=[]
for ins in C.dis_range(0x85d000,0x880000):
    rva=ins.address-C.IB
    for tok in ins.op_str.replace("["," ").replace("]"," ").replace(","," ").split():
        if tok.startswith("0x"):
            try: v=int(tok,16)
            except Exception: continue
            if 0x400000<=v<0x0e659000:
                r=v-C.IB
                if 0x8a8000<=r<0xa65000 or 0x990000<=r<0xa65000:
                    s=get(r)
                    if s: hits.append((rva, hex(r), s))
seen=set(); uniq=[]
for rva,tgt,s in hits:
    if (tgt,s) in seen: continue
    seen.add((tgt,s)); uniq.append((rva,tgt,s))
o=io.open(os.path.join(C.EV,"modattr_85d000_880000.txt"),"w",encoding="utf-8",newline="")
o.write("count=%d\n"%len(uniq))
for rva,tgt,s in uniq[:200]:
    o.write("  %08x %-12s %s\n"%(rva,tgt,s[:120]))
o.close()
print("wrote", len(uniq))
