#!/usr/bin/env python3
"""深挖：21/1 #25 位置的 u64 分布、DEADC0DE 魔数、11/4 的 blob 内容。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 1) 21/1 里所有 u64 元素的取值（按元素序号）
print("=== 21/1 每个 u64 元素位置的取值分布 ===")
pos = collections.defaultdict(collections.Counter)
for r in corpus:
    if (r["svc"], r["task"]) != (21, 1):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for j, (t, v) in enumerate(els):
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            pos[j][int.from_bytes(v, "little")] += 1
for j in sorted(pos):
    print("  元素 #%d : %s" % (j, dict(pos[j].most_common(4))))

# 2) DEADC0DE 魔数全语料搜索
print("\n=== DEADC0DE 全语料搜索 ===")
nd = bytes.fromhex("dec0adde")
hits = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    c = b.count(nd)
    if c:
        hits[(r["svc"], r["task"])] += c
print("  bytes 'de c0 ad de' :", dict(hits), "合计", sum(hits.values()))

# 3) 该 u64 完整值 0x01100001deadc0de 的上下文
print("\n=== u64 == 0x01100001deadc0de 的上下文 ===")
n = 0
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for j, (t, v) in enumerate(els):
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            if int.from_bytes(v, "little") == 0x01100001deadc0de:
                parts = []
                for k, (tt, vv) in enumerate(els):
                    if tt == 0x13:
                        parts.append("13[%d]" % len(vv))
                    elif isinstance(vv, bytes) and len(vv) <= 8:
                        parts.append("%02x=%d" % (tt, int.from_bytes(vv, "little")))
                    else:
                        parts.append("%02x" % tt)
                print("  %d/%d len=%d: %s" % (r["svc"], r["task"], len(b), " ".join(parts)[:400]))
                n += 1
                break
    if n >= 2:
        break

# 4) 11/4 的 blob 内容（145B / 21B）
print("\n=== 11/4 的 blob 内容样本 ===")
seen = set()
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) not in seen:
            seen.add(len(v))
            print("  [%dB] %s" % (len(v), v[:80].hex(" ")))
    if len(seen) >= 5:
        break
