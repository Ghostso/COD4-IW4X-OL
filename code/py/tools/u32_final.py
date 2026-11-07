#!/usr/bin/env python3
"""0x08 收尾统计：{0,1} 占比、>65535 占比、按值大小的分桶、0x08->0x08 连簇长度。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

vals = []
runs_of_08 = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    # 连簇
    run = 0
    for t, v in els:
        if t == 0x08:
            run += 1
        else:
            if run:
                runs_of_08[run] += 1
            run = 0
        if t == 0x08 and isinstance(v, bytes) and len(v) == 4:
            vals.append(int.from_bytes(v, "little"))
    if run:
        runs_of_08[run] += 1

n = len(vals)
print("u32 字段 = %d" % n)
buckets = {"0": 0, "1": 0, "2..9": 0, "10..99": 0, "100..999": 0,
           "1000..65535": 0, "65536..2^31": 0, ">2^31": 0}
for v in vals:
    if v == 0:
        buckets["0"] += 1
    elif v == 1:
        buckets["1"] += 1
    elif v < 10:
        buckets["2..9"] += 1
    elif v < 100:
        buckets["10..99"] += 1
    elif v < 1000:
        buckets["100..999"] += 1
    elif v <= 65535:
        buckets["1000..65535"] += 1
    elif v <= 2**31 - 1:
        buckets["65536..2^31"] += 1
    else:
        buckets[">2^31"] += 1
for k, c in buckets.items():
    print("  %-14s %-6d %.1f%%" % (k, c, 100.0 * c / n))

print("\n{0,1} 合计 = %d = %.1f%%" % (buckets["0"] + buckets["1"], 100.0 * (buckets["0"] + buckets["1"]) / n))

print("\n=== 0x08 连续簇长度分布 ===")
for k in sorted(runs_of_08):
    print("  %d 连  x%d" % (k, runs_of_08[k]))

# 值 >= 100000 的总出现数
big = sum(1 for v in vals if v >= 100000)
print("\n值 >= 100000 的字段数 = %d (%.1f%%)" % (big, 100.0 * big / n))
