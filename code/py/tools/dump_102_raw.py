#!/usr/bin/env python3
"""转储 102/7、102/1、102/5 的原始 payload 字节, 精确核对结构。"""
import json

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, "r", encoding="utf-8"))
if isinstance(recs, dict):
    recs = recs.get("records") or recs.get("data") or list(recs.values())

def hexd(b):
    return " ".join("%02x" % c for c in b)

seen = {}
for r in recs:
    svc = r.get("svc"); task = r.get("task")
    if svc == 102:
        key = task
        p = bytes.fromhex(r["payload"])
        seen.setdefault(key, []).append((r.get("run"), r.get("idx"), p))

for task in sorted(seen):
    lst = seen[task]
    print("\n=== 102/%s  条数=%d ===" % (task, len(lst)))
    # 打印前3条, 以及长度分布
    lens = {}
    for run, idx, p in lst:
        lens[len(p)] = lens.get(len(p), 0) + 1
    print("  长度分布:", dict(sorted(lens.items())))
    for run, idx, p in lst[:3]:
        print("  [%s #%s] len=%d" % (run, idx, len(p)))
        print("     " + hexd(p[:200]) + (" ..." if len(p) > 200 else ""))
    # 首 8 字节 & 末 8 字节
    p0 = lst[0][2]
    print("  首8: " + hexd(p0[:8]) + "   末8: " + hexd(p0[-8:]))
