# -*- coding: utf-8 -*-
"""Search for CoD-style message handler tables: clusters of adjacent imm32 code
pointers in .rdata/.data, and for the client-command vocabulary. Read-only."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
CODE_LO,CODE_HI=0x1000,0x8a8000
# Find runs of >=6 consecutive little-endian dwords that land in code section
def runs(lo,hi,minrun=6):
    out=[]; i=lo
    while i<hi-4:
        j=i; n=0
        while j<hi-4:
            v=struct.unpack("<I", b[j:j+4])[0]
            r=v-C.IB
            if CODE_LO<=r<CODE_HI and (r%1==0):
                n+=1; j+=4
            else: break
        if n>=minrun:
            out.append((i,n)); i=j
        else:
            i+=4
    return out
# scan data-ish sections present: 0x8a8000..0xa65000
R=runs(0x8a8000,0xa65000, minrun=6)
print("candidate pointer tables (>=6 code ptrs):", len(R))
R.sort(key=lambda t:-t[1])
for off,n in R[:40]:
    vals=[hex(struct.unpack('<I',b[off+4*k:off+4*k+4])[0]-C.IB) for k in range(min(n,10))]
    print("  %08x n=%3d  %s" % (off,n,vals))
