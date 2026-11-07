#!/usr/bin/env python3
"""0x03 (u8) 的取值分布 + 非 1 值来源；0x01 bool 的 3 个 false 是谁。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

u8 = collections.Counter()
u8_task = collections.Counter()
u8_nonone = collections.Counter()
bool_false = []
bool_by_task = collections.Counter()

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for j, (t, v) in enumerate(els):
        if t == 0x03:
            x = v[0]
            u8[x] += 1
            u8_task[(r["svc"], r["task"])] += 1
            if x != 1:
                prev = els[j - 1][0] if j else None
                nxt = els[j + 1][0] if j + 1 < len(els) else None
                u8_nonone[(r["svc"], r["task"], x, prev, nxt)] += 1
        if t == 0x01:
            x = v[0]
            bool_by_task[(r["svc"], r["task"], x)] += 1
            if x == 0:
                bool_false.append((r["svc"], r["task"], r["idx"], j, len(els)))

print("=== 0x03 u8 的取值分布（top15）===")
for k, v in u8.most_common(15):
    print("  value %-4d : %d" % (k, v))
print("  不同取值个数: %d" % len(u8))

print("\n=== 0x03 非 1 值的来源 (task, value, prevtag, nexttag) top20 ===")
for k, v in u8_nonone.most_common(20):
    print("  %3d/%-4d val=%-4d prev=%s next=%s : %d" % (
        k[0], k[1], k[2],
        "%02x" % k[3] if k[3] is not None else "-",
        "%02x" % k[4] if k[4] is not None else "-", v))

print("\n=== 0x01 bool 的 (task, value) 分布 ===")
for k, v in bool_by_task.most_common(20):
    print("  %3d/%-4d bool=%d : %d" % (k[0], k[1], k[2], v))

print("\n=== bool == 0 的 3 个样本 ===")
for s in bool_false:
    print("  %d/%d idx=%s elem#%d of %d" % s)
