# -*- coding: utf-8 -*-
import sys, os, io, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)
def callers(t):
    tv=C.IBI+t; rr=[]; i=0x1000
    while i<0x8a8000-5:
        if b[i]==0xE8:
            rel=struct.unpack("<i",b[i+1:i+5])[0]
            if (C.IBI+i)+5+rel==tv: rr.append(i)
        i+=1
    return rr
for t in (0x879AC0,0x879C40):
    emit("callers of %08x : %s"%(t,[hex(x) for x in callers(t)]))
# strings referenced anywhere in 0x879AC0 function range (widen to 0x879AC0..0x879D80) incl .rdata lower
emit("")
emit("=== string refs in 0x879AC0..0x879D80 (range 0x7xx000..0xa65000) ===")
for k in C.idis_range(0x879AC0,0x879D80):
    for tok in k.op_str.replace("["," ").replace("]"," ").replace(","," ").split():
        if tok.startswith("0x"):
            try: v=int(tok,16)
            except: continue
            r=v-C.IBI
            if 0x743000<=r<0xa65000:
                s=C.icstr(r,50)
                if s and len(s)>=5 and all(32<=c<127 for c in s):
                    emit("  %08x -> %08x %s"%(k.address-C.IBI,r,s.decode('latin1')[:60]))
io.open(os.path.join(C.EV,"c_879AC0_attr.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
