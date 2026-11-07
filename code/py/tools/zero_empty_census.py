#!/usr/bin/env python3
"""空负载与终止符长度分布：0x00 作为"整个 payload"的场合。"""
import collections
import json
import sys

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
allzero = collections.Counter()
one_zero = 0
for r in corpus:
    b = bytes.fromhex(r["payload"])
    if not b:
        continue
    if b.count(0) == len(b):
        allzero[(r["svc"], r["task"], len(b))] += 1
    if len(b) == 1 and b[0] == 0:
        one_zero += 1

print("全零 payload（整条只有 0x00）条数: %d" % sum(allzero.values()))
for k, v in allzero.most_common(15):
    print("  %d/%d  len=%d  ×%d" % (k[0], k[1], k[2], v))
print("payload 恰为单个 0x00 的条数: %d" % one_zero)
