#!/usr/bin/env python3
"""全语料 service/task 普查：每条 task 的报文数、payload 长度分布、典型 payload hex。
用于识别尚未语义定名的 task。"""
import collections
import json
import sys

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

per = collections.defaultdict(list)
for r in corpus:
    per[(r["svc"], r["task"])].append(r)

print("=== 全部 service/task (%d 个) ===" % len(per))
rows = []
for k in sorted(per):
    recs = per[k]
    lens = [r["len"] for r in recs]
    rows.append((k[0], k[1], len(recs), min(lens), max(lens), sum(lens) // len(lens)))

print("%-4s %-4s %-6s %-5s %-5s %-5s" % ("svc", "task", "count", "minL", "maxL", "avgL"))
for r in sorted(rows, key=lambda x: (-x[2], x[0], x[1])):
    print("%-4d %-4d %-6d %-5d %-5d %-5d" % r)
