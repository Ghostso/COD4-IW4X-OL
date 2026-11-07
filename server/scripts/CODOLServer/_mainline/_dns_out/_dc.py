import csv, re, collections
rows=[]
with open("dns.csv", encoding="gbk", errors="replace") as f:
    for r in csv.DictReader(f):
        rows.append(r)
print("总行:", len(rows))
print("列名:", list(rows[0].keys())[:30])
print()
# 找含域名/结果的列
names=[(k,[v for v in (r.get(k) or "").strip() for r in rows[:200] if (r.get(k) or "").strip()][:3]) for k in rows[0].keys()]
for k,sample in names:
    if sample: print("  %-40s %s"%(k, sample[:2]))
