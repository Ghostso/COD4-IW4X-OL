#!/usr/bin/env python3
"""0xff 专项：区分 (a) 独立整型字段=255/-1  (b) blob 内 0xff 的局部结构。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402
import zero_role_census2 as Z  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

exact = collections.Counter()
contains = collections.Counter()
blob_task = collections.Counter()
blob_runlen = collections.Counter()
ff_run_ctx = collections.Counter()

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    rm = {}
    Z.walk(G.Buf(b), b, rm)
    for t, v in els:
        if t in G.FIXED and isinstance(v, bytes) and len(v) == G.FIXED[t]:
            iv = int.from_bytes(v, "little", signed=(t == 0x07))
            if iv == 0xFF:
                exact[(r["svc"], r["task"], hex(t))] += 1
            if 0xFF in v and iv != 0xFF:
                contains[(r["svc"], r["task"], hex(t), v.hex(), iv)] += 1
    # blob 内连续 0xff 串
    i = 0
    n = len(b)
    while i < n:
        if b[i] == 0xFF:
            j = i
            while j < n and b[j] == 0xFF:
                j += 1
            L = j - i
            if all(rm.get(k) == "B" for k in range(i, j)):
                blob_task[(r["svc"], r["task"])] += L
                blob_runlen[L] += 1
                ff_run_ctx[(L, b[i - 1] if i else -1, b[j] if j < n else -1)] += 1
            i = j
        else:
            i += 1

print("=== 独立整型字段值恰为 0xFF(255) 或 -1 ===")
for k, v in exact.most_common(20):
    print("  %d/%d %s : %d" % (k[0], k[1], k[2], v))
print("\n=== 含 0xFF 但整体值不是 0xFF 的整型字段 ===")
for k, v in contains.most_common(12):
    print("  %d/%d %s %s = %d : x%d" % (k[0], k[1], k[2], k[3], k[4], v))
print("\n=== blob 内 0xFF 总字节数 按 task ===")
for k, v in blob_task.most_common(12):
    print("  %d/%d : %d" % (k[0], k[1], v))
print("\n=== blob 内 0xFF 连续长度分布 ===")
for k, v in sorted(blob_runlen.items()):
    print("  len=%d x%d" % (k, v))
print("\n=== blob 内 0xFF 串 (len, pre, post) top12 ===")
for k, v in ff_run_ctx.most_common(12):
    pa = "%02x" % k[1] if k[1] >= 0 else "ST"
    pc = "%02x" % k[2] if k[2] >= 0 else "EN"
    print("  %s <%s x%d> %s : x%d" % (pa, "ff", k[0], pc, v))
