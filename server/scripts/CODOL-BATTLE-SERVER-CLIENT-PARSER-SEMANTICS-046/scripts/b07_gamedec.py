# -*- coding: utf-8 -*-
"""b07: map the real game-protocol decoder region and how it is fed."""
import sys, os, struct, bisect
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
starts=[]
i=0x1000
while i<0x8a7000:
    if C._img[i]==0xCC:
        j=i
        while j<0x8a7000 and C._img[j]==0xCC: j+=1
        if j-i>=2: starts.append(j)
        i=j
    else: i+=1
starts=sorted(set(starts))
def fs(a):
    k=bisect.bisect_right(starts,a)-1; return starts[k] if k>=0 else None
for a in (0x66F410,0x671FF9,0x66FDA0,0x670B1C,0x672067,0x672080,0x673267,0x6733D8,0x6732EC):
    print("  0x%06X -> func 0x%06X"%(a, fs(a) or 0))
print()
# callers of the decoder container(s)
for t in (0x66F410,0x671FD0,0x673040,0x422A90,0x464913):
    cs=C.e8_callers(t); print("  func 0x%06X E8 callers: %s"%(t,[hex(x) for x,_ in cs]))
