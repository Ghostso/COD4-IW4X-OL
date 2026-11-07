#!/usr/bin/env python3
"""复核 21/1 #25、21/12 #27、11/2 #0 的 u64 取值；11/4 两种 u64 与 run 的关系。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
ACC = 0xE7C8A98A6B4C2D0E
CH = 0x1122334455667788


def u64s(els):
    return [(i, int.from_bytes(v, "little")) for i, (t, v) in enumerate(els)
            if t == 0x0A and isinstance(v, bytes) and len(v) == 8]


for svc, task, pos in [(21, 1, 25), (21, 12, 27), (11, 2, 0)]:
    print("\n=== %d/%d 元素#%d 的取值 ===" % (svc, task, pos))
    c = collections.Counter()
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        u = dict(u64s(els))
        if pos in u:
            v = u[pos]
            tag = "ACC" if v == ACC else ("CH" if v == CH else ("ACClo32" if v == (ACC & 0xFFFFFFFF) else "?"))
            c[(v, tag)] += 1
    for k, n in c.most_common():
        print("   %d (0x%X) [%s] x%d" % (k[0], k[0], k[1], n))

# 11/4: 两种 u64 分别出现在哪些 run
print("\n=== 11/4 两种 u64 的 run 分布 ===")
c = collections.defaultdict(collections.Counter)
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    u = u64s(els)
    if u:
        v = u[0][1]
        c[r.get("run")][v] += 1
for run, cnt in sorted(c.items()):
    lab = {CH: "CH", 1800154382: "ACClo32"}
    print("  %-28s %s" % (run, {lab.get(k, hex(k)): n for k, n in cnt.items()}))
