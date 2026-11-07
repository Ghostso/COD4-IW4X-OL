#!/usr/bin/env python3
"""深挖：为何只有 3 个 run 用 ACClo32 当 roomId；这些 run 有何不同。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
ACC = 0xE7C8A98A6B4C2D0E
CH = 0x1122334455667788
ACClo = ACC & 0xFFFFFFFF
ODD = {"ONCE_20261029_000806", "ONCE_20261029_001513", "ONCE_20261029_002046"}

for run in sorted(ODD):
    print("\n########## %s ##########" % run)
    recs = [r for r in corpus if r.get("run") == run]
    print("  报文数 = %d" % len(recs))
    c = collections.Counter((r["svc"], r["task"]) for r in recs)
    print("  task 分布:", dict(c))
    # 该 run 里所有 u64 值
    u = collections.Counter()
    for r in recs:
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        for t, v in els:
            if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
                u[int.from_bytes(v, "little")] += 1
    print("  u64 值:", {("ACC" if k == ACC else "CH" if k == CH else "ACClo" if k == ACClo else k): n for k, n in u.items()})

# 对比：一个正常 run 的 u64
print("\n########## 正常 run 对比 ONCE_20261029_103202 ##########")
run = "ONCE_20261029_103202"
recs = [r for r in corpus if r.get("run") == run]
u = collections.Counter()
for r in recs:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            u[int.from_bytes(v, "little")] += 1
print("  u64 值:", {("ACC" if k == ACC else "CH" if k == CH else "ACClo" if k == ACClo else k): n for k, n in u.items()})

# 全局：ACClo 是否只在这 3 run
print("\n=== 全语料出现 ACClo 的 run ===")
runs = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8 and int.from_bytes(v, "little") == ACClo:
            runs[r.get("run")] += 1
            break
for k, n in runs.items():
    print("  %s  x%d" % (k, n))
