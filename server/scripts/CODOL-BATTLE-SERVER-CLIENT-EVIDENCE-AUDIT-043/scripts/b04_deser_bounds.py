# -*- coding: utf-8 -*-
"""Phase B: exact boundaries of 0x87C110 and 0x87D5A0 and the [ebx+8] dispatch
instruction census. Read-only."""
import sys, os, io, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._bi; out=[]
def emit(s): out.append(s)

def find_cc_run(lo,hi):
    res=[]
    i=lo
    while i<hi-2:
        if b[i]==0xCC and b[i+1]==0xCC and b[i+2]==0xCC:
            e=i
            while e<hi and b[e]==0xCC: e+=1
            res.append((i,e)); i=e
        else: i+=1
    return res

def report_entry(f, label):
    emit("=== %s @ %08x ==="%(label,f))
    rets=[]
    vend=f
    for k in C.idis_range(f, f+0x2000):
        if k.mnemonic=="ret":
            rets.append(k.address-C.IBI)
    emit("  ret sites: %s"%[hex(x) for x in rets[:12]])
    # assume function end = last ret before a >=8 cc run
    pads=find_cc_run(f, f+0x2000)
    if pads:
        emit("  first >=3 CC pad after entry: %08x..%08x"%(pads[0][0],pads[0][1]))
    return rets, pads

report_entry(0x87C110,"deser#1")
report_entry(0x87D5A0,"deser#2")

# instruction census of [ebx+8] and element loop patterns in 0x87C110 region
emit("")
emit("=== [ebx+8] / [ebx+0x8] references inside 0x87C110..0x87D593 ===")
seen=[]
for k in C.idis_range(0x87C110, 0x87D593):
    if re.search(r"\[ebx \+ 8\]", k.op_str):
        seen.append((k.address-C.IBI, k.mnemonic, k.op_str))
for a,m,o in seen: emit("  %08x %-8s %s"%(a,m,o))
emit("  total: %d"%len(seen))

# count distinct constants compared
emit("")
emit("=== cmp imm forms in 0x87C110..0x87D593 (first 60) ===")
n=0
for k in C.idis_range(0x87C110, 0x87D593):
    if k.mnemonic in ("cmp","sub","add") and re.search(r"0x[0-9a-f]+", k.op_str):
        n+=1
        if n<=60: emit("  %08x %-8s %s"%(k.address-C.IBI,k.mnemonic,k.op_str))
emit("  total cmp/sub/add-with-imm: %d"%n)
io.open(os.path.join(C.EV,"dis_deser_boundaries.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
