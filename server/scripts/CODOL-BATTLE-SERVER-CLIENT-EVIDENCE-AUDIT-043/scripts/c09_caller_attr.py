# -*- coding: utf-8 -*-
"""Phase C: attribute caller functions 0x879AC0 / 0x85D3A0 / 0x85D430 / 0x85D5A0
by .rdata/.data string references. Read-only."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
out=[]
def emit(s): out.append(s)
def strrefs(lo,hi):
    got=[]
    for k in C.idis_range(lo,hi):
        for tok in k.op_str.replace("["," ").replace("]"," ").replace(","," ").split():
            if tok.startswith("0x"):
                try: v=int(tok,16)
                except: continue
                r=v-C.IBI
                if 0x8a8000<=r<0xa65000:
                    s=C.icstr(r,60)
                    if s and len(s)>=4 and all(32<=c<127 for c in s):
                        got.append((k.address-C.IBI,hex(r),s.decode('latin1')))
    # dedupe
    seen=set(); uniq=[]
    for a,r,s in got:
        if (r,s) in seen: continue
        seen.add((r,s)); uniq.append((a,r,s))
    return uniq
for lo,hi,lab in [(0x879AC0,0x879D80,"0x879AC0 (calls sizeinfo encoders)"),
                  (0x85D3A0,0x85D430,"0x85D3A0"),
                  (0x85D430,0x85D500,"0x85D430 (calls deser1)"),
                  (0x85D5A0,0x85DA90,"0x85D5A0 (calls deser2/read)")]:
    emit("=== string refs in %s ==="%lab)
    R=strrefs(lo,hi)
    if not R: emit("  (none found in .rdata/.data range)")
    for a,r,s in R[:25]:
        emit("  %08x -> %s  %s"%(a,r,s[:80]))
    emit("")
io.open(os.path.join(C.EV,"c_caller_attr_strings.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
