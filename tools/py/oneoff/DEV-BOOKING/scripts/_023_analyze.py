# -*- coding: utf-8 -*-
import os, re
from collections import Counter
D = r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"
p = os.path.join(D, "accepted_state.txt")
rows = []
for ln in open(p, encoding="utf-8", errors="replace"):
    if not ln.startswith("["): continue
    ts = ln[1:ln.index("]")] if "]" in ln else ""
    d = {"ts": ts, "tag": ln.split("]",1)[1].strip().split(" ")[0] if "]" in ln else ""}
    for m in re.finditer(r"([A-Za-z0-9_]+)=([0-9A-Fa-fx\-]+)", ln):
        d[m.group(1)] = m.group(2)
    rows.append(d)
print("rows =", len(rows))
for f in ["this288_byte","this288_word","this278","A","B","flag849B61C","t_5E8","t_C8","this1C","this283"]:
    c = Counter(r.get(f,"-") for r in rows)
    print("  %-14s %s" % (f, dict(c.most_common(6))))
print("--- rows where this288_byte != 0 ---")
n=0
for r in rows:
    if r.get("this288_byte") not in (None,"0","-1"):
        print("   ", r.get("ts"), r.get("tag"), r.get("this288_byte"), r.get("this278"), r.get("A"), r.get("B")); n+=1
print("   count =", n)
print("--- A/B transitions ---")
prev=None; shown=0
for r in rows:
    if r.get("A") is None: continue
    k=(r.get("A"),r.get("B"),r.get("this278"),r.get("this288_byte"))
    if k!=prev:
        print("   %s A=%s B=%s this278=%s this288=%s flag=%s t_5E8=%s" % (r.get("ts"),r.get("A"),r.get("B"),r.get("this278"),r.get("this288_byte"),r.get("flag849B61C",r.get("flag","-")),r.get("t_5E8")))
        prev=k; shown+=1
        if shown>20: print("   ..."); break
