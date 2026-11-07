# -*- coding: utf-8 -*-
"""gen_hashes_046.py - build SHA256SUMS.txt + FILE_HASH_MANIFEST.tsv for the whole task dir."""
import os, hashlib, sys
sys.stdout.reconfigure(encoding="utf-8")
T=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<20), b""): h.update(c)
    return h.hexdigest()
rows=[]
for root,dirs,files in os.walk(T):
    dirs[:] = [d for d in dirs if d!="__pycache__"]
    for fn in files:
        if fn in ("SHA256SUMS.txt","FILE_HASH_MANIFEST.tsv"): continue
        p=os.path.join(root,fn); rel=os.path.relpath(p,T).replace("\\","/")
        rows.append((rel, os.path.getsize(p), sha(p)))
rows.sort()
lines=["%s  %s"%(h,rel) for rel,_,h in rows]
open(os.path.join(T,"SHA256SUMS.txt"),"w",encoding="utf-8",newline="\n").write("\n".join(lines)+"\n")
man=["relative_path\tbytes\tsha256\tcategory"]
for rel,b,h in rows:
    cat = ("input" if rel.startswith("_input/") else
           "extracted" if rel.startswith("_extracted/") else
           "evidence" if rel.startswith("evidence/") else
           "script" if rel.startswith("scripts/") else
           "deliverable" if rel.endswith(".md") else "other")
    man.append("%s\t%d\t%s\t%s"%(rel,b,h,cat))
open(os.path.join(T,"FILE_HASH_MANIFEST.tsv"),"w",encoding="utf-8",newline="\n").write("\n".join(man)+"\n")
print("files:",len(rows))
from collections import Counter
print(Counter(r[0].split("/")[0] for r in rows))

