# -*- coding: utf-8 -*-
"""Map the net-buffer reader family: prologues, string refs, and callers. Read-only."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
# find prologues near each ref
refs=[0x87cddb,0x87cdaa,0x87cb98,0x87c80a,0x87decc,0x87e5ba,0x87e306]
def prologue_before(off, back=0x400):
    i=off
    while i>max(0x1000,off-back):
        if b[i-3:i]==b"\x55\x8b\xec": return i-3
        i-=1
    return None
funcs=sorted(set(prologue_before(r) for r in refs))
print("referencing functions (prologue RVA):", [hex(x) if x else None for x in funcs])
for f in funcs:
    if f is None: continue
    ins=C.dis_at(f,15)
    print("  func %08x : %s %s" % (f, ins.mnemonic, ins.op_str))
# who calls these functions? scan E8 rel32 in first .tp3
code_lo,code_hi=0x1000,0x8a8000
callsites={f:[] for f in funcs if f}
i=code_lo
while i<code_hi-5:
    if b[i]==0xE8:
        rel=struct.unpack("<i", b[i+1:i+5])[0]
        tgt=(C.IB+i)+5+rel
        tr=tgt-C.IB
        if tr in callsites:
            callsites[tr].append(i)
    i+=1
for f,cs in callsites.items():
    print("  callers of %08x : %s" % (f, [hex(x) for x in cs[:20]]))
