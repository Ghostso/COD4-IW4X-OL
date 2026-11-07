#!/usr/bin/env python3
"""从 6/14 mmstart 明文抽出含 2486/2489/2574/2500/3265 的整行/片段。"""
import json, re
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

TARGETS=["2486","2489","2574","2500","3265"]
found={t:set() for t in TARGETS}
for r in recs:
    if r.get("svc")==6 and r.get("task")==14:
        p=bytes.fromhex(r["payload"])
        # 明文段 (mmstart)
        txt=p.decode("latin1",errors="replace")
        for t in TARGETS:
            # 抓该数字前后 40 字符
            for m in re.finditer(re.escape(t), txt):
                lo=max(0,m.start()-45); hi=min(len(txt),m.end()+45)
                snip=txt[lo:hi]
                # 只保留可打印
                snip="".join(ch if 32<=ord(ch)<127 else "." for ch in snip)
                found[t].add(snip)

for t in TARGETS:
    print("\n=== %s (%d 个不同上下文) ==="%(t,len(found[t])))
    for s in list(found[t])[:6]:
        print("   ...%s..."%s)
