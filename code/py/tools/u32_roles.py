#!/usr/bin/env python3
"""0x08 角色分账校验：tag 数 / 整型载荷中的 0x08 / L / B；并核 0x13/6b/6c 数量。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402
import zero_role_census2 as Z  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

roles = collections.Counter()
tagcnt = 0
total_bytes = 0
struct_markers = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    total_bytes += len(b)
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        tagcnt += 1
        if t in (0x13, 0x6B, 0x6C):
            struct_markers[t] += 1
    rm = {}
    Z.walk(G.Buf(b), b, rm)
    for i, x in enumerate(b):
        if x == 0x08:
            roles[rm.get(i, "?")] += 1

print("总字节 = %d" % total_bytes)
print("元素总数 = %d" % tagcnt)
print("0x13/0x6b/0x6c 元素数 = %s  合计=%d" % (dict(struct_markers), sum(struct_markers.values())))
print("\n0x08 角色分账: %s  合计=%d" % (dict(roles), sum(roles.values())))
print("  其中 F(含标签字节) = %d ; 减去标签 6369 后纯载荷 = %d" % (roles['F'], roles['F'] - 6369))
print("  占比 = %.3f%% of all bytes" % (100.0 * sum(roles.values()) / total_bytes))
