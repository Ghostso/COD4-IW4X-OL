#!/usr/bin/env python3
"""8/3 的 ID 族结构：10000+ 与 30000+ 区间，以及 0x07 标签/值歧义统计。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402
import zero_role_census2 as Z  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

ids = sorted([10001, 10010, 10015, 10028, 10042, 10049, 10106, 30059, 30060, 30061])
print("=== 8/3 的 ID 族结构 ===")
prev = None
for x in ids:
    d = "" if prev is None else "  Δ=%d" % (x - prev)
    print("  %-6d 0x%04x%s" % (x, x, d))
    prev = x

print("\n=== 0x07 的标签/值歧义（按角色）===")
roles = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    rm = {}
    Z.walk(G.Buf(b), b, rm)
    for i, x in enumerate(b):
        if x == 0x07:
            roles[rm.get(i, "?")] += 1
print("  0x07 字节的角色分布:", dict(roles))

# 0x07 作为标签（H）的次数 = 元素个数
cnt = 0
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    cnt += sum(1 for t, v in els if t == 0x07)
print("  0x07 作为标签的元素数: %d" % cnt)

print("\n=== 各标签的 0x07 首字节 vs 值 ===")
# 有多少 0x07 字段的值 < 256（即首字节是值本身而非 0）
small = 0
total = 0
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x07 and isinstance(v, bytes) and len(v) == 4:
            total += 1
            iv = int.from_bytes(v, "little", signed=True)
            if 0 <= iv < 256:
                small += 1
print("  i32 字段 %d 个，其中 0<=v<256 的 %d 个 (%.1f%%)" % (total, small, 100.0 * small / total))
