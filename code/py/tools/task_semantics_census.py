#!/usr/bin/env python3
"""§七 #2: ~15 个"只有结构无业务语义"的 task —— 全量普查。
   对每个 task 给出: 条数 / 长度 / distinct 数 / 首字节 / 是否固定 / host 名(若有) / 可读 ASCII
   目标: 区分 遥测(71/*) vs 固定常量 vs 需要真 RE 的。
"""
import json, struct, collections, re
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
by=collections.defaultdict(list)
for r in recs:
    by[(r.get("svc"),r.get("task"))].append(bytes.fromhex(r["payload"]))

print("=== 全 55 task 普查 ===")
print("%-8s %5s %-14s %7s %s"%("svc/task","n","len range","distinct","摘要"))
for k in sorted(by):
    xs=by[k]; lens=[len(x) for x in xs]
    distinct=len(set(xs))
    fixed="FIXED" if distinct==1 else ""
    # 可读 ASCII 片段
    ascii_bits=set()
    for x in xs[:3]:
        for m in re.finditer(rb"[ -~]{5,}",x):
            ascii_bits.add(m.group(0)[:40].decode("latin1","replace"))
    summary=" ".join(sorted(ascii_bits)[:3]) if ascii_bits else xs[0][:12].hex()
    print("%-8s %5d %-14s %7d %-6s %s"%("%d/%d"%k,len(xs),
          "%d..%d"%(min(lens),max(lens)),distinct,fixed,summary[:70]))
