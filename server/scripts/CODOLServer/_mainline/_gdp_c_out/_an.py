import json
p="state.jsonl"
recs=[json.loads(l) for l in open(p,encoding="utf-8") if l.strip()]
prev=None
for r in recs:
    k=(r.get("state"),r.get("cur_name"))
    if k!=prev:
        print("  t=%7.2f state=%-4s cur=%-10s name=%r res=%s"%(r["t"],r.get("state"),hex(r["cur"]) if r.get("cur") else None,r.get("cur_name"),r.get("res")))
        prev=k
print()
print("采样=%d"%len(recs))
