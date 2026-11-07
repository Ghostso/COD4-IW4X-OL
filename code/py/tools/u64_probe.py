#!/usr/bin/env python3
"""0x0a (u64) 的字段值全分布：102/7 的 50 个 ID 序列、真实 u64 ID、魔数。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

vals = collections.Counter()
task_vals = collections.defaultdict(collections.Counter)
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            u = int.from_bytes(v, "little")
            vals[u] += 1
            task_vals[(r["svc"], r["task"])][u] += 1

tot = sum(vals.values())
print("=== 0x0a u64 字段总数 %d，不同取值 %d ===" % (tot, len(vals)))
print("\n=== 值频 top25 ===")
for k, v in vals.most_common(25):
    print("  %-22d (0x%016x) : %d" % (k, k, v))

print("\n=== 按 task 的 u64 字段 ===")
for k in sorted(task_vals, key=lambda x: -sum(task_vals[x].values())):
    tv = task_vals[k]
    n = sum(tv.values())
    print("  %3d/%-4d  %-6d 个, distinct=%-5d top3=%s" % (
        k[0], k[1], n, len(tv), [(x, y) for x, y in tv.most_common(3)]))
