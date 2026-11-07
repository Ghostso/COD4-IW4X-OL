#!/usr/bin/env python3
"""71/3 71/7 71/15 遥测事件名全枚举: 格式 EventName|${time}|value.
   抽出所有 EventName token 与 ${...} 时间表达式种类 → 收口 §七 #2 的遥测部分."""
import json, collections, re
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

def payloads(svc,task):
    return [bytes.fromhex(r["payload"]) for r in recs if r.get("svc")==svc and r.get("task")==task]

for svc,task in [(71,3),(71,7)]:
    ps=payloads(svc,task)
    names=collections.Counter()
    timeexpr=collections.Counter()
    for p in ps:
        txt=p.decode("latin1","replace")
        for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\|(\$\{[^}]*\})",txt):
            names[m.group(1)]+=1
            tm=re.match(r"\$\{([A-Za-z_]+)",m.group(2))
            if tm: timeexpr[tm.group(1)]+=1
    print("=== %d/%d : %d 条 ==="%(svc,task,len(ps)))
    print("  事件名 (%d 种):"%len(names))
    for n,c in names.most_common():
        print("    %-28s x%d"%(n,c))
    print("  时间表达式种类:",dict(timeexpr.most_common()))
    # 一条完整样本
    if ps:
        s=max(ps,key=len)
        print("  最长样本(%dB): %r"%(len(s),s[:300]))
    print()

# 71/15 是什么? 看首尾
ps=payloads(71,15)
print("=== 71/15 : %d 条, distinct=%d ==="%(len(ps),len(set(ps))))
for p in sorted(set(ps),key=len)[:2]:
    print("  len=%d hex[:60]=%s"%(len(p),p[:60].hex()))
    print("  ascii=%r"%p[:80].decode("latin1","replace"))
