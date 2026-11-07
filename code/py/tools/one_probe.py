#!/usr/bin/env python3
"""0x01 深挖：值恰为 1 的整型字段 vs 字节恰好是 0x01 的载荷。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402
import zero_role_census2 as Z  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

val1 = collections.Counter()     # 字段值恰为 1
boolfield = collections.Counter()  # 0x01 标签的 bool 值
bytag_total = collections.Counter()
bytag_one = collections.Counter()

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t in G.FIXED and isinstance(v, bytes) and len(v) == G.FIXED[t]:
            iv = int.from_bytes(v, "little", signed=(t == 0x07))
            bytag_total[t] += 1
            if iv == 1:
                bytag_one[t] += 1
                val1[(r["svc"], r["task"], hex(t))] += 1
            if t == 0x01:
                boolfield[iv] += 1

print("=== 各标签：总数 / 值恰为 1 的数量 / 比例 ===")
for t in sorted(bytag_total):
    tot = bytag_total[t]
    one = bytag_one[t]
    print("  tag %02x : 总 %-6d  值=1 %-6d  %.1f%%" % (t, tot, one, 100.0 * one / tot))

print("\n=== 0x01 (bool) 标签的全部取值分布 ===")
for k, v in sorted(boolfield.items()):
    print("  bool = %-6d : %d" % (k, v))

print("\n=== 值恰为 1 的字段 (task, tag) top20 ===")
for k, v in val1.most_common(20):
    print("  %3d/%-4d tag %s : %d" % (k[0], k[1], k[2], v))
