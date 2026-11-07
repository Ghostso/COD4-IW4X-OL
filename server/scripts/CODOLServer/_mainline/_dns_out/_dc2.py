import csv, re, collections
rows=[]
with open("dns.csv", encoding="gbk", errors="replace") as f:
    for r in csv.DictReader(f): rows.append(r)
dns=[r for r in rows if "DNS" in (r.get("  Event Name") or "")]
print("DNS 事件:", len(dns))
# 收集所有 hostname 形态
names=collections.Counter()
status=collections.Counter()
for r in dns:
    ud=r.get(" User Data") or ""
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9._-]{3,80}\.[A-Za-z]{2,10}", ud):
        names[m.group().strip('.')]+=1
    for m in re.finditer(r"(?:Status|status)\D{0,3}(0x[0-9a-fA-F]+|\d+)", ud):
        status[m.group(1)]+=1
print()
print("=== 出现过的域名 ===")
for n,c in names.most_common(40): print("  %-45s x%d"%(n,c))
print()
print("=== 状态码统计 ===")
for s,c in status.most_common(15): print("  %-12s x%d"%(s,c))
print()
print("=== 样例 User Data (前 3 条 DNS 事件) ===")
for r in dns[:3]:
    print("  ", (r.get(" User Data") or "")[:400])
