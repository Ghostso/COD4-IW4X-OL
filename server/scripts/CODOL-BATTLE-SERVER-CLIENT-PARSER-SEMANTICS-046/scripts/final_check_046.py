# -*- coding: utf-8 -*-
"""independent final check: recompute every hash in SHA256SUMS.txt"""
import os,hashlib,sys
sys.stdout.reconfigure(encoding="utf-8")
T=os.getcwd()
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()
ok=bad=miss=0; probs=[]
for line in open("SHA256SUMS.txt",encoding="utf-8"):
    line=line.rstrip("\n")
    if not line: continue
    h,rel=line.split("  ",1)
    p=os.path.join(T,rel.replace("/",os.sep))
    if not os.path.exists(p): miss+=1; probs.append("MISSING "+rel); continue
    a=sha(p)
    if a==h: ok+=1
    else: bad+=1; probs.append("MISMATCH "+rel)
print("SHA256SUMS.txt verification: OK=%d BAD=%d MISS=%d"%(ok,bad,miss))
for x in probs[:20]: print("  ",x)
# echo the deliverable hashes for the final report
for f in sorted(os.listdir(T)):
    if f.endswith(".md"): print("  %s  %s"%(sha(os.path.join(T,f))[:16], f))
print("TOTAL md deliverables:", sum(1 for f in os.listdir(T) if f.endswith(".md")))
