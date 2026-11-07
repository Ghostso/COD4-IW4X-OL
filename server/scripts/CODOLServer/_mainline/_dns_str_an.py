import json, collections
p=r"CODOLServer\_mainline\_dns_str_out\dns.jsonl"
recs=[json.loads(l) for l in open(p,encoding="utf-8") if l.strip()]
print("采样=%d"%len(recs))
print()
print("=== sa_static (0x81A76A8) 取值集合 ===")
for v,c in collections.Counter(r.get("sa_static") for r in recs).most_common(8): print("   %r x%d"%(v,c))
print()
print("=== objA/objB/res/state 变化点 ===")
prev=None
for r in recs:
    key=(r.get("objA"),r.get("objB"),r.get("res"),r.get("state"),r.get("cur"))
    if key!=prev:
        print("   t=%7.2f objA=%-10s objB=%-10s res=%-6s state=%-4s cur=%s"%(r["t"],r.get("objA"),r.get("objB"),r.get("res"),r.get("state"),hex(r["cur"]) if r.get("cur") else None))
        prev=key
print()
print("=== sa_deref 取值集合 ===")
for v,c in collections.Counter(r.get("sa_deref") for r in recs).most_common(8): print("   %r x%d"%(v,c))
print()
print("=== objA_field 取值集合（前 6）===")
for v,c in collections.Counter(r.get("objA_field") for r in recs).most_common(6): print("   0x%X x%d"%(v,c) if isinstance(v,int) else "   %r x%d"%(v,c))
