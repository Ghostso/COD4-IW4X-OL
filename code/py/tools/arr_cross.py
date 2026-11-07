#!/usr/bin/env python3
"""跨任务关联：每个 run 的 28/1(tail/body) 与 21/5(playlist) 的关系，判定 28/1 语义。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 收集每个 run 的 21/5 playlist（第 3 个 u32）与 28/1 tail 集合
run_215 = collections.defaultdict(list)
run_281 = collections.defaultdict(list)
run_order = collections.defaultdict(list)

for r in corpus:
    run = r.get("run")
    key = (r["svc"], r["task"])
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    if key == (21, 5):
        # 21/5: 08 01 | 08 00 | 08 <playlist> | 07 A | 6b
        u32s = [int.from_bytes(v, "little") for t, v in els if t == 0x08]
        if len(u32s) >= 3:
            run_215[run].append(u32s[2])
    if key == (28, 1):
        for t, v in els:
            if t == 0x6C:
                cnt, body = v
                u = [int.from_bytes(body[j:j+4], "little") for j in range(0, len(body) - len(body) % 4, 4)]
                run_281[run].append((u[0] if u else 0, tuple(u[1:]), cnt))
    run_order[run].append((r["idx"], key, r["svc"], r["task"]))

print("=== 每 run: 21/5 playlist vs 28/1 (N,items,tail) ===")
allruns = sorted(set(list(run_215) + list(run_281)))
for run in allruns:
    pl = sorted(set(run_215.get(run, [])))
    t281 = run_281.get(run, [])
    if pl or t281:
        print("  %-26s 21/5_playlist=%-12s 28/1=%s" % (run, pl, t281))

# 统计 tail 与 playlist 的对应
print("\n=== tail(28/1) 分布 vs playlist(21/5) ===")
pair = collections.Counter()
for run in allruns:
    pls = set(run_215.get(run, []))
    tails = set(t[2] for t in run_281.get(run, []))
    for pl in pls:
        for tl in tails:
            pair[(pl, tl)] += 1
for (pl, tl), n in sorted(pair.items()):
    print("  playlist=%-4d tail=%-4d x%d" % (pl, tl, n))
