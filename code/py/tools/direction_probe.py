#!/usr/bin/env python3
"""方向判定：corpus 的 run/idx 结构、每个 run 内 task 序列、以及"同 task 是否成对出现"。"""
import collections
import json
import sys

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("=== corpus 顶层字段 ===")
print("  键:", sorted(corpus[0].keys()))
print("  记录数:", len(corpus))

runs = collections.Counter(r["run"] for r in corpus)
print("\n=== run 分布 ===")
for k, v in runs.most_common(20):
    print("  run=%s : %d 条" % (k, v))

print("\n=== 每个 run 的 (svc/task) 计数 top ===")
per_run = collections.defaultdict(collections.Counter)
for r in corpus:
    per_run[r["run"]][(r["svc"], r["task"])] += 1
for run in list(per_run)[:6]:
    print("  --- run=%s ---" % run)
    for k, v in per_run[run].most_common(12):
        print("     %d/%d : %d" % (k[0], k[1], v))

# idx 是否单调 / 是否 per-run 重置
print("\n=== idx 单调性检查（每个 run）===")
for run in list(per_run)[:6]:
    idxs = [r["idx"] for r in corpus if r["run"] == run]
    print("  run=%s  n=%d  min=%s max=%s  严格递增=%s" % (
        run, len(idxs), min(idxs), max(idxs),
        all(idxs[i] < idxs[i+1] for i in range(len(idxs)-1))))
