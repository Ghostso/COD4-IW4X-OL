# -*- coding: utf-8 -*-
"""Callers of the net-buffer reader family + search for socket/recv machinery in
the unpacked image. Read-only."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
code_lo,code_hi=0x1000,0x8a8000
def callers_of(target_rva, limit=40):
    tv=C.IB+target_rva; out=[]; i=code_lo
    while i<code_hi-5:
        if b[i]==0xE8:
            rel=struct.unpack("<i", b[i+1:i+5])[0]
            if (C.IB+i)+5+rel==tv: out.append(i)
        i+=1
    return out[:limit]
for t in (0x87a890,0x87ae00,0x87d588,0x87ee17):
    print("callers of %08x : %s" % (t,[hex(x) for x in callers_of(t)]))

# string search for network receive machinery
import re
def allstrings(minlen=5):
    out=[]; i=0; cur=bytearray(); st=0
    while i<len(b):
        c=b[i]
        if 32<=c<127:
            if not cur: st=i
            cur.append(c)
        else:
            if len(cur)>=minlen: out.append((st,cur.decode("latin1")))
            cur=bytearray()
        i+=1
    return out
S=allstrings()
KW=[r"recv", r"Recv", r"WSARecv", r"recvfrom", r"send", r"Send", r"socket", r"Socket",
    r"net_", r"Net_", r"udp", r"UDP", r"connectionless", r"reliable", r"reliab",
    r"CMD_", r"cmd ", r"NetChan", r"netchan", r"packet", r"Packet"]
seen=set(); res=[]
for off,s in S:
    for p in KW:
        if re.search(p,s):
            if (off,s) in seen: break
            seen.add((off,s)); res.append((off,s)); break
print("\n=== network-ish strings (%d) ===" % len(res))
for off,s in res[:120]:
    print("  %08x  %s" % (off, s[:120]))
