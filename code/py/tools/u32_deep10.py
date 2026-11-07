#!/usr/bin/env python3
"""0x08 深挖十：service 4 全 task 清单；4/13 #0 与时间/序号的关联；4/x 在 run 中的位置。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("=== service 4 的全部 task ===")
c = collections.Counter()
for r in corpus:
    if r["svc"] == 4:
        c[r["task"]] += 1
print("  ", dict(c))

print("\n=== service 4 在 ONCE_20261029_143736 里的出现顺序（task, idx, 首 u32）===")
rows = []
for r in corpus:
    if r["svc"] != 4 or r.get("run") != "ONCE_20261029_143736":
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    first = None
    if good and els and els[0][0] == 0x08:
        first = int.from_bytes(els[0][1], "little")
    rows.append((r.get("idx"), r["task"], first, len(b)))
rows.sort(key=lambda x: (x[0] if isinstance(x[0], int) else 0))
for x in rows[:40]:
    print("   idx=%s task=%d first=%s len=%d" % x)

print("\n=== 4/13 各 run 的 #0 值集合 ===")
per = collections.defaultdict(collections.Counter)
for r in corpus:
    if (r["svc"], r["task"]) != (4, 13):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if good and els:
        per[r.get("run")][int.from_bytes(els[0][1], "little")] += 1
for run, cnt in sorted(per.items()):
    print("   %-28s %s" % (run, dict(cnt)))
