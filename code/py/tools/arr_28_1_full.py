#!/usr/bin/env python3
"""28/1 任务参数全语料：payload 形态、0x6c body 与 run 的关系、是否编码关卡/地图。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("=== 28/1 全部报文形态 ===")
forms = collections.Counter()
byrun = collections.defaultdict(list)
for r in corpus:
    if (r["svc"], r["task"]) != (28, 1):
        continue
    b = bytes.fromhex(r["payload"])
    forms[b.hex()] += 1
    byrun[r.get("run")].append(b.hex())

print("distinct payload = %d, total = %d" % (len(forms), sum(forms.values())))
for h, n in forms.most_common(20):
    print("  x%-3d %s" % (n, h))

print("\n=== 每个 run 的 28/1 序列 ===")
for run in sorted(byrun):
    seq = byrun[run]
    print("  %s : %d 条  %s" % (run, len(seq), seq))
