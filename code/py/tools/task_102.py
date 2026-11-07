#!/usr/bin/env python3
"""102/* 深挖：在每个 run 中的位置（与其它 task 的相对顺序），判断它属于哪个阶段。"""
import collections
import json
import sys

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 按 run 分组，看 102/* 前后邻居 task
run_recs = collections.defaultdict(list)
for r in corpus:
    run_recs[r.get("run")].append((r["idx"], r["svc"], r["task"]))

print("=== 102/* 在每个 run 中的位置（前后各 3 个 task）===")
shown = 0
for run in sorted(run_recs):
    recs = sorted(run_recs[run])
    for i, (idx, svc, task) in enumerate(recs):
        if svc == 102:
            lo = max(0, i - 3)
            hi = min(len(recs), i + 4)
            ctx = ["%d/%d" % (s, t) if s != 102 else "*%d/%d*" % (s, t) for _, s, t in recs[lo:hi]]
            print("  %s idx=%d  ctx: %s" % (run, idx, " -> ".join(ctx)))
            shown += 1
            break
    if shown >= 12:
        break

# 102/* 与哪些 task 在同 run 共存（最常一起出现）
print("\n=== 102/* 与其它 task 的共现（同 run）===")
co = collections.Counter()
for run in run_recs:
    tasks = set((s, t) for _, s, t in run_recs[run])
    if any(s == 102 for s, t in tasks):
        for s, t in tasks:
            if s != 102:
                co[(s, t)] += 1
for k, n in co.most_common(15):
    print("  %d/%d  x%d" % (k[0], k[1], n))

# 102/1 的两种形态
print("\n=== 102/1 两种形态 ===")
forms = collections.Counter(r["payload"] for r in corpus if (r["svc"], r["task"]) == (102, 1))
for hx, n in forms.most_common():
    print("  x%d %s" % (n, hx))
