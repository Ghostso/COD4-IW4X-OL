# -*- coding: utf-8 -*-
"""Mine the unpacked image for engine function-name-ish symbols related to
network/messages/parsing. Read-only."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
def allstrings(minlen=4):
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
# symbol-ish patterns
pats=[r"\bnet_?\w+", r"^\?\?\w*net", r"\bNetChan\w*", r"\bMsg\w+", r"\bmsg_\w+",
      r"\bCL_\w+", r"\bSV_\w+", r"\bCG_\w+", r"parse\w+", r"\bdecode\w+", r"\bRead\w+",
      r"\bReassemble\w*", r"\bsvc\w+", r"\bOOB\w*", r"\boob\w+", r"\bClient\w*Command\w*",
      r"\bCmd\w+"]
seen=set()
out=[]
for off,s in S:
    for p in pats:
        if re.search(p, s):
            key=(off,s)
            if key in seen: break
            seen.add(key)
            out.append((off,s)); break
print("symbol-ish strings:", len(out))
for off,s in out:
    print("  %08x  %s" % (off, s[:130]))
