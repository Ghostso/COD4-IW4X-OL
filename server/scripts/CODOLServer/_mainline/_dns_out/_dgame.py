import csv,re
rows=[]
with open("dns.csv", encoding="gbk", errors="replace") as f:
    for r in csv.DictReader(f): rows.append(r)
pidkey=[k for k in rows[0].keys() if k.strip()=="PID"][0]
udkey=[k for k in rows[0].keys() if k.strip()=="User Data"][0]
idkey=[k for k in rows[0].keys() if k.strip()=="Event ID"][0]
ctkey=[k for k in rows[0].keys() if k.strip()=="Clock-Time"][0]
dns=[r for r in rows if "DNS" in (r.get("  Event Name") or "") and (r.get(pidkey) or "").strip().lower()=="0x00004018"]
print("游戏进程 DNS 事件:", len(dns))
for r in dns:
    print("  ID=%-4s t=%-14s  %s"%( (r.get(idkey) or '').strip(), (r.get(ctkey) or '').strip()[:14], (r.get(udkey) or '')[:150]))
