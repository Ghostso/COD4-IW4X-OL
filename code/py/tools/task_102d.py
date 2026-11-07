#!/usr/bin/env python3
"""102/7 的 0a 值是否全语料都是 0..49（序号，恒定），还是随 run 变。
若是恒定序号 => 是"槽位/条目列表"而非时间戳。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

vals_sets = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (102, 7):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    vals = [int.from_bytes(v, "little") for t, v in els if t == 0x0A]
    vals_sets[tuple(vals)] += 1

print("=== 102/7 的 0a 序列去重 ===")
print("distinct = %d" % len(vals_sets))
for k, n in vals_sets.most_common(3):
    print("  x%d vals[:10]=%s len=%d" % (n, list(k)[:10], len(k)))

# 102/1 的 0a 值分布
print("\n=== 102/1 的 0a 值分布 ===")
c = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (102, 1):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    vals = tuple(int.from_bytes(v, "little") for t, v in els if t == 0x0A)
    keys = tuple(int.from_bytes(v, "little") for t, v in els if t == 0x03)
    c[(keys, vals)] += 1
for (keys, vals), n in c.most_common():
    print("  keys=%s vals=%s x%d" % (keys, vals, n))

# 102/1 的第二个 08 值（元素数）分布
print("\n=== 102/1 第 2 个 u32（元素数）分布 ===")
c2 = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (102, 1):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    u32s = [int.from_bytes(v, "little") for t, v in els if t == 0x08]
    if len(u32s) >= 2:
        c2[u32s[1]] += 1
print("  ", dict(c2))
