#!/usr/bin/env python3
"""28/1 & 28/4 的 tail(cnt) 语义判定。
28/4: tail=263 = 客户端能解锁的总容量; body[0]=127 = 本次查询的项数。
28/1: body=[N][idx...]; tail=? 若 tail 是"可选总数"，则 body 里的 idx 应 < tail。
看 28/1 tail 与 body 值的所有组合，并判定 body item 是否是"索引"。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def all_6c():
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        for t, v in els:
            if t == 0x6C:
                cnt, body = v
                u = [int.from_bytes(body[j:j+4], "little") for j in range(0, len(body) - len(body) % 4, 4)]
                yield (r["svc"], r["task"], u, cnt, r.get("run"))


print("=== 28/1 完整 (N, items, tail) 与 run 分组 ===")
byrun = collections.defaultdict(list)
for svc, task, u, cnt, run in all_6c():
    if (svc, task) == (28, 1):
        byrun[run].append((u[0] if u else 0, tuple(u[1:]), cnt))

# 统计 (N, items, tail) 全局组合
c = collections.Counter()
for svc, task, u, cnt, run in all_6c():
    if (svc, task) == (28, 1):
        c[(u[0] if u else 0, tuple(u[1:]), cnt)] += 1
print("全局组合:")
for (N, items, tail), n in c.most_common():
    print("  N=%d items=%-8s tail=%-4d x%d" % (N, list(items), tail, n))

print("\n=== 判定 tail 语义 ===")
print("28/4: N(body[0])=127, tail=263 => tail=total capacity, body is 'unlocked subset'")
print("  126 items max check: 262 < 263? True")

# 28/4 items 的最大值
for svc, task, u, cnt, run in all_6c():
    if (svc, task) == (28, 4):
        items = u[1:]
        print("  28/4 items: min=%d max=%d n=%d ; all < tail(263)? %s" %
              (min(items), max(items), len(items), all(x < cnt for x in items)))
        break

# 28/1: body item 是否 < tail
print("\n28/1 body item < tail 检查:")
for svc, task, u, cnt, run in all_6c():
    if (svc, task) == (28, 1) and len(u) > 1:
        items = u[1:]
        print("  items=%s tail=%d all<tail? %s" % (items, cnt, all(x < cnt for x in items)))
