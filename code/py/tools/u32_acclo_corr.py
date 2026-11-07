#!/usr/bin/env python3
"""验证：出现 ACClo 的 run 是否 = 有 11/13(createRoom) 的 run；反之亦然。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
ACC = 0xE7C8A98A6B4C2D0E
ACClo = ACC & 0xFFFFFFFF

runs = collections.defaultdict(lambda: {"tasks": collections.Counter(), "acclo": 0})
for r in corpus:
    run = r.get("run")
    runs[run]["tasks"][(r["svc"], r["task"])] += 1
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8 and int.from_bytes(v, "little") == ACClo:
            runs[run]["acclo"] += 1
            break

print("%-28s %-6s %-8s %-8s %-8s %-8s" % ("run", "ACClo", "11/13", "11/4", "11/2", "21/1"))
for run in sorted(runs):
    d = runs[run]
    has_cr = d["tasks"][(11, 13)]
    print("%-28s %-6d %-8d %-8d %-8d %-8d" % (
        run, d["acclo"], has_cr, d["tasks"][(11, 4)], d["tasks"][(11, 2)], d["tasks"][(21, 1)]))

# 交叉表
print("\n=== 交叉：有 ACClo vs 有 11/13 ===")
a = sum(1 for d in runs.values() if d["acclo"] and d["tasks"][(11, 13)])
b = sum(1 for d in runs.values() if d["acclo"] and not d["tasks"][(11, 13)])
c = sum(1 for d in runs.values() if not d["acclo"] and d["tasks"][(11, 13)])
e = sum(1 for d in runs.values() if not d["acclo"] and not d["tasks"][(11, 13)])
print("  ACClo & 11/13 : %d" % a)
print("  ACClo & !11/13: %d" % b)
print("  !ACClo & 11/13: %d" % c)
print("  !ACClo & !11/13: %d" % e)
