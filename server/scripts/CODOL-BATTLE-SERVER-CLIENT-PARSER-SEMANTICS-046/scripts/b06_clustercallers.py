# -*- coding: utf-8 -*-
import sys, os, struct, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
# function starts from int3 padding
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
import bisect
def fstart(a):
    k=bisect.bisect_right(starts,a)-1
    return starts[k] if k>=0 else None
# candidate cluster functions holding socket ops
cands={}
for i in range(0x1000,0x8a7000-6):
    if C._img[i]==0xFF and C._img[i+1] in (0x15,0x25):
        v=struct.unpack_from("<I",C._img,i+2)[0]
        if v in (0xCA84E4,0xCA84E8,0xCA851C,0xCA84E0,0xCA8518,0xCA8500,0xCA84FC):
            fs=fstart(i); cands.setdefault(fs,[]).append(i)
print("cluster funcs holding socket ops:")
for fs in sorted(cands):
    cs=C.e8_callers(fs)
    print("  0x%08X sites=%s callers=%s"%(fs, [hex(x) for x in cands[fs]], [hex(a) for a,_ in cs]))
