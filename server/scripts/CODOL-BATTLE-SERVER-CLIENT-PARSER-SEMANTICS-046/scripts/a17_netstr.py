# -*- coding: utf-8 -*-
import sys, os, struct, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
def s(rva, ml=400):
    b=C.raw(rva,ml)
    if b is None: return None
    e=b.find(b"\x00"); return b[:e].decode("latin1","replace")
print("string @ VA 0xD9EB88 ->", repr(s(0xD9EB88-IB)))
print()
# 042 claimed net-buffer diagnostic strings 0x99EE98..0x99F428
print("=== dump 0x99EE98..0x99F428 strings ===")
lo,hi=0x99EE98,0x99F428
i=lo
while i<hi:
    b=C._img[i:i+1]
    if b and 32<=b[0]<127:
        j=i
        while j<hi and 32<=C._img[j]<127: j+=1
        if j-i>=4: print("  0x%08X %r"%(i,C._img[i:j].decode("latin1")))
        i=j
    else: i+=1
