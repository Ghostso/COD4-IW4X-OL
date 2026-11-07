#!/usr/bin/env python3
"""0x08 (u32) 标签专卷探针：字段数/值域/按 task 分布/值==1 占比/特殊值。"""
import collections
import json
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

vals = collections.Counter()
by_task = collections.Counter()
task_vals = collections.defaultdict(collections.Counter)
pos_in_msg = collections.Counter()
seq_next = collections.Counter()
nfields = 0
zero = one = 0

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for idx, (t, v) in enumerate(els):
        if t != 0x08 or not isinstance(v, bytes) or len(v) != 4:
            continue
        nfields += 1
        iv = int.from_bytes(v, "little", signed=False)
        vals[iv] += 1
        by_task[(r["svc"], r["task"])] += 1
        task_vals[(r["svc"], r["task"])][iv] += 1
        if iv == 0:
            zero += 1
        if iv == 1:
            one += 1
        if idx + 1 < len(els):
            seq_next[(t, els[idx + 1][0])] += 1

print("u32 字段总数 = %d" % nfields)
print("不同取值 = %d" % len(vals))
print("== 0 : %d (%.1f%%)" % (zero, 100.0 * zero / nfields))
print("== 1 : %d (%.1f%%)" % (one, 100.0 * one / nfields))

print("\n=== 值 top20 ===")
for k, n in vals.most_common(20):
    print("  %-12d 0x%08x  x%d" % (k, k, n))

print("\n=== 按 task 字段数 top20 ===")
for k, n in by_task.most_common(20):
    tv = task_vals[k]
    print("  %d/%-3d  fields=%-5d distinct=%-5d top=%s" % (
        k[0], k[1], n, len(tv), tv.most_common(3)))

print("\n=== 紧跟的标签（0x08 之后下一个元素）===")
for (a, c), n in seq_next.most_common(10):
    print("  0x%02x -> 0x%02x  x%d" % (a, c, n))

# 大值（>65535）样本，用于看是否像 build 号/时间戳
print("\n=== 值 > 100000 的全部样本 ===")
big = [(k, n) for k, n in vals.items() if k > 100000]
big.sort(key=lambda x: -x[1])
for k, n in big[:30]:
    print("  %-12d 0x%08x  x%d" % (k, k, n))
print("  ... 共 %d 种大值" % len(big))
