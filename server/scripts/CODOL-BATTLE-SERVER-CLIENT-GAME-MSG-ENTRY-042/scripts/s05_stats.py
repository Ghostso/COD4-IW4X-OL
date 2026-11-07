# -*- coding: utf-8 -*-
"""Dump the .data receiver-stats region and find .text references (imm32) to it,
plus resolve nearby strings. Read-only."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C

def cstr(r, ml=160):
    o=C.rva2off(r)
    if o is None: return None
    e=C._b.find(b"\0",o,o+ml)
    if e<0: e=o+ml
    return C._b[o:e]

# dump strings in .data 0xa02000..0xa04000
print("=== .data 0xa02800..0xa03000 strings ===")
base=0xa02800
o=C.rva2off(base)
chunk=C._b[o:o+0x800]
i=0; cur=bytearray(); st=0
while i<len(chunk):
    c=chunk[i]
    if 32<=c<127:
        if not cur: st=i
        cur.append(c)
    else:
        if len(cur)>=4:
            print("  %08x %s"%(base+st, cur.decode('latin1')))
        cur=bytearray()
    i+=1

# find imm32 refs to key stats strings in .text
targets={}
for nm in (b"CSRecvPkgCount",b"GSRecvPkgCount",b"RecvSuccPkgCount",b"RecvFailPkgCount",b"LastRecvPkgSeq"):
    j=C._b.find(nm)
    while j>=0:
        r=C.off2rva(j)
        if r is not None and C.sec_of_rva(r)==".data":
            targets[nm.decode()]=r; break
        j=C._b.find(nm,j+1)
print("\n=== target string RVAs ===")
for k,v in targets.items(): print("  %s = %08x (VA %08x)"%(k,v,v+C.IB))

# scan .text for imm32 references to any target
def scan_imm32(target_va):
    pat=struct.pack("<I",target_va); hits=[]; i=0; n=len(C._td)
    while i<=n-4:
        j=C._td.find(pat,i)
        if j<0: break
        hits.append(C._text["va"]+j); i=j+1
    return hits
print("\n=== imm32 refs in .text ===")
for k,v in targets.items():
    h=scan_imm32(v+C.IB)
    print("  %-18s : %s"%(k,[hex(x) for x in h[:20]]))
