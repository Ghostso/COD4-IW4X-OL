import csv,re,collections,subprocess
rows=[]
with open("dns.csv", encoding="gbk", errors="replace") as f:
    for r in csv.DictReader(f): rows.append(r)
# 取 PID 列
pidkey=[k for k in rows[0].keys() if k.strip()=="PID"][0]
udkey=[k for k in rows[0].keys() if k.strip()=="User Data"][0]
dns=[r for r in rows if "DNS" in (r.get("  Event Name") or "")]
# 进程名映射
names={}
try:
    out=subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True).stdout.decode('gbk','replace')
    for line in out.splitlines():
        p=[x.strip('"') for x in line.split('","')]
        if len(p)>=2: names[p[1]]=p[0]
except Exception: pass
agg=collections.defaultdict(collections.Counter)
for r in dns:
    pid=(r.get(pidkey) or "").strip()
    ud=r.get(udkey) or ""
    m=re.search(r"([A-Za-z0-9][A-Za-z0-9._-]{3,80}\.[A-Za-z]{2,10})", ud)
    if m: agg[pid][m.group(1)]+=1
print("=== 按 PID 汇总 DNS 查询 ===")
for pid,c in sorted(agg.items(), key=lambda kv:-sum(kv[1].values())):
    print("PID %-8s (%-24s) 共%d次"%(pid, names.get(pid,"?"), sum(c.values())))
    for n,k in c.most_common(8):
        print("      %-45s x%d"%(n,k))
