# -*- coding: utf-8 -*-
"""Dump readable strings in the EXE region 0x690000..0x6b6000 (raw file offsets)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
data=C._bex
lo,hi=0x690000,0x6b6000
chunk=data[lo:hi]
i=0; cur=bytearray(); st=0; out=[]
while i<len(chunk):
    c=chunk[i]
    if 32<=c<127:
        if not cur: st=i
        cur.append(c)
    else:
        if len(cur)>=5:
            out.append((lo+st, cur.decode("latin1")))
        cur=bytearray()
    i+=1
print("strings:", len(out))
for off,s in out[:400]:
    print("  %08x %s" % (off, s[:120]))
