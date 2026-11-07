#!/usr/bin/env python3
"""0x07 (i32 标签) 的字段值全分布：符号、量级、高频值、按 task。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

vals = collections.Counter()
neg = pos = zero = 0
task_cnt = collections.Counter()
task_vals = collections.defaultdict(collections.Counter)
pos_hist = collections.Counter()
neg_hist = collections.Counter()

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t != 0x07 or not isinstance(v, bytes) or len(v) != 4:
            continue
        iv = int.from_bytes(v, "little", signed=True)
        vals[iv] += 1
        task_cnt[(r["svc"], r["task"])] += 1
        task_vals[(r["svc"], r["task"])][iv] += 1
        if iv == 0:
            zero += 1
        elif iv < 0:
            neg += 1
            neg_hist[iv] += 1
        else:
            pos += 1
            pos_hist[iv] += 1

tot = sum(vals.values())
print("=== 0x07 i32 字段：总 %d 个 ===" % tot)
print("  零 %d (%.1f%%)  正 %d (%.1f%%)  负 %d (%.1f%%)" % (
    zero, 100.0 * zero / tot, pos, 100.0 * pos / tot, neg, 100.0 * neg / tot))
print("  不同取值个数: %d" % len(vals))

print("\n=== 值频 top25 ===")
for k, v in vals.most_common(25):
    print("  %-14d : %d" % (k, v))

print("\n=== 负值 top15 ===")
for k, v in neg_hist.most_common(15):
    print("  %-14d : %d" % (k, v))

print("\n=== 正值 top15 ===")
for k, v in pos_hist.most_common(15):
    print("  %-14d : %d" % (k, v))

print("\n=== 按 task 的 i32 字段数 top15 ===")
for k, v in task_cnt.most_common(15):
    tv = task_vals[k]
    print("  %3d/%-4d  %-6d 个, distinct=%-5d top3=%s" % (
        k[0], k[1], v, len(tv), tv.most_common(3)))
