# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b

def all_strings(minlen=3):
    out=[]; cur=bytearray(); start=0
    for i,ch in enumerate(b):
        if 0x20 <= ch < 0x7f:
            if not cur: start=i
            cur.append(ch)
        else:
            if len(cur)>=minlen:
                r=C.off2rva(start)
                if r is not None: out.append((r, cur.decode("latin1")))
            cur=bytearray()
    return out
S=all_strings(3)
pat=re.compile(r"(^|[^a-z])(ping|latency|echo reply|echo request|icmp|round.?trip|server.?list)([^a-z]|$)", re.I)
hits=[(r,s) for r,s in S if pat.search(s)]
print("strict hits:",len(hits))
for r,s in hits[:40]:
    print("  0x%08X [%s] %r" % (r,C.sec_of_rva(r),s[:80]))
print()
# strings within 0x220000..0x240000 in .rdata
near=[(r,s) for r,s in S if 0x740000<=r<0x770000 and 100<=len(s)<=90]
print("sample .rdata strings with 'ping' substring anywhere:")
for r,s in S:
    if 0x740000<=r<0x9b0000 and 'ping' in s.lower():
        print("  0x%08X %r" % (r,s[:80]))
