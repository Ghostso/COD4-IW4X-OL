#!/usr/bin/env python3
"""列出语料里服务 6 与 102 的 task 分布; 以及全服务清单(条数)。"""
import json, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
svc=collections.defaultdict(lambda: collections.Counter())
for r in recs:
    svc[r["svc"]][r["task"]]+=1
print("=== 全服务 (svc: 总条数) ===")
for s in sorted(svc):
    tot=sum(svc[s].values())
    print("  svc %3d : %5d 条   tasks=%s" % (s, tot, dict(sorted(svc[s].items()))))
print("\n=== svc 6 详情 ===")
for t,c in sorted(svc[6].items()): print("  6/%d : %d"%(t,c))
print("\n=== svc 102 详情 ===")
for t,c in sorted(svc[102].items()): print("  102/%d : %d"%(t,c))
