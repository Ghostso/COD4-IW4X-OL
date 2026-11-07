# -*- coding: utf-8 -*-
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
b=C._b

# find all ascii strings and filter keywords
def all_strings(minlen=4):
    out=[]
    cur=bytearray(); start=0
    for i,ch in enumerate(b):
        if 0x20 <= ch < 0x7f:
            if not cur: start=i
            cur.append(ch)
        else:
            if len(cur)>=minlen:
                r=C.off2rva(start)
                out.append((r, cur.decode("latin1")))
            cur=bytearray()
    return out

S=all_strings(4)
import re
kw = re.compile(r"icmp|ping|echo|rtt|latency|probe|traceroute|network|packet|raw socket|checksum", re.I)
hits=[(r,s) for r,s in S if r and kw.search(s)]
print("keyword string hits:", len(hits))
for r,s in hits[:60]:
    print("  0x%08X [%s] %s" % (r, C.sec_of_rva(r), s[:120]))
