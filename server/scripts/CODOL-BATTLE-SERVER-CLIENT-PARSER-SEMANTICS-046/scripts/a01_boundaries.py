# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C

# Locate function boundaries in the 0x85D2xx..0x85EB5x cluster using int3 padding + prologues.
lo, hi = 0x85D200, 0x85EC00
# find runs of CC (padding) 
runs=[]
i=lo
while i<hi:
    if C._img[i]==0xCC:
        j=i
        while j<hi and C._img[j]==0xCC: j+=1
        if j-i>=3: runs.append((i,j))
        i=j
    else: i+=1
print("=== int3 padding runs (>=3) in 0x%X..0x%X ==="%(lo,hi))
for a,b in runs: print("  pad %08X..%08X (%d)"%(a,b,b-a))
