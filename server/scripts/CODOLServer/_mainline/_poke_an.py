import json
p=r"CODOLServer\_mainline\_poke_out\poke.jsonl"
recs=[json.loads(l) for l in open(p,encoding="utf-8") if l.strip()]
print("采样=%d"%len(recs))
prev=None
for r in recs:
    k=(r.get("cur_s"),r.get("state"),r.get("res"),r.get("objA"))
    if k!=prev:
        print("  t=%7.2f cur=%-14r state=%-4s res=%-4s objA=%-4s h1=%r"%(r["t"],r.get("cur_s"),r.get("state"),r.get("res"),r.get("objA"),(r.get("h1") or "")[:24]))
        prev=k
print()
import collections
print("=== cur_s 取值集合 ===")
for v,c in collections.Counter(r.get("cur_s") for r in recs).most_common(8): print("   %r x%d"%(v,c))
print()
print("=== objA / res / state 是否曾非0 ===")
for k in ("objA","objB","res","state"):
    vals=[r.get(k) for r in recs]
    print("   %-5s 非零=%d/%d  %s"%(k,len([v for v in vals if v]),len(vals),sorted(set(vals))[:6]))
