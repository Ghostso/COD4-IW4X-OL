import csv,re
rows=[]
with open(r"CODOLServer\_mainline\_dns_out\dns.csv", encoding="gbk", errors="replace") as f:
    for r in csv.DictReader(f): rows.append(r)
dns=[r for r in rows if "DNS" in (r.get("  Event Name") or "")]
idx=[i for i,r in enumerate(dns) if "hipcapi" in (r.get(" User Data") or "")]
print("含 hipcapi 的事件数:", len(idx), " 首现序号:", idx[:5])
for i in idx[:2]:
    print("--- 事件 %d ---"%i)
    print("   UserData:", (dns[i].get(" User Data") or "")[:500])
print()
print("=== 每个域名的首次出现顺序（时间线）===")
seen=[]
for i,r in enumerate(dns):
    ud=r.get(" User Data") or ""
    m=re.search(r"[A-Za-z0-9][A-Za-z0-9._-]{3,80}\.[A-Za-z]{2,10}", ud)
    if m and m.group(0) not in seen:
        seen.append(m.group(0))
for n in seen[:30]: print("   ", n)
