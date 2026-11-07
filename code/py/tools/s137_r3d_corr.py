#!/usr/bin/env python3
"""s137 R3d: 932 的取值集合/上下文/与已知量的算术关系（逐一试）. 纯静态."""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
ACCT = 0xE7C8A98A6B4C2D0E
BUILD = 1649370

# 收集 4/13 与 4/4 的 (run, idx, elem0)
data = {}
for svc, task in ((4, 13), (4, 4)):
    rows = []
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        x = int.from_bytes(els[0][1], "little")
        rows.append((r.get("run"), r.get("idx"), x))
    data[(svc, task)] = rows

allv = collections.Counter()
for k, rows in data.items():
    for _, _, x in rows:
        allv[x] += 1
print("=== 4/13 ∪ 4/4 elem#0 取值集合 ===")
print("  distinct=%d" % len(allv))
for v, n in allv.most_common():
    print("    %-8d 0x%X  x%d" % (v, v, n))

print("\n=== 与已知量的算术关系 (X=932) ===")
X = 932
tests = {
    "== acct_low32": X == (ACCT & 0xFFFFFFFF),
    "== acct_high32": X == (ACCT >> 32),
    "== build": X == BUILD,
    "== build_low16": X == (BUILD & 0xFFFF),
    "== build_high16": X == (BUILD >> 16),
    "acct_low32 % 932": (ACCT & 0xFFFFFFFF) % X,
    "acct %% 932": ACCT % X,
    "build %% 932": BUILD % X,
    "build // 932": BUILD // X,
    "0x1122334455667788 %% 932": 0x1122334455667788 % X,
    "0x1122334455667788 & 0xFFFF": 0x1122334455667788 & 0xFFFF,
    "acct & 0xFFFF": ACCT & 0xFFFF,
    "acct >> 48": ACCT >> 48,
    "acct_low32 >> 16": (ACCT & 0xFFFFFFFF) >> 16,
    "932 == 0x3A4 (yes)": True,
    "932 == 2*466": 932 == 2 * 466,
    "932 == 4*233": 932 == 4 * 233,
    "932 hex digits": 0x3A4,
    "932 = 365*86400 mod ?": (365 * 86400) % X,
    "48988830? ": 0,
}
for k, v in tests.items():
    print("  %-32s %s" % (k, v))

print("\n=== 933/931/932 邻域: 是否 0x3A4 与 0x3EC(1004) 之类成对 ===")
print("  0x3A4=%d  0x3EC=%d  diff=%d" % (0x3A4, 0x3EC, 0x3EC - 0x3A4))
print("  100,108,113,118,123,135,148 -> 差分:",
      [b - a for a, b in zip([100, 108, 113, 118, 123, 135, 148],
                             [108, 113, 118, 123, 135, 148])])

print("\n=== 每个 run 的 4/13 elem0 集合 (非全932的) ===")
perrun = collections.defaultdict(collections.Counter)
for run, idx, x in data[(4, 13)]:
    perrun[run][x] += 1
for run, c in sorted(perrun.items()):
    if set(c) != {932}:
        print("  %s -> %s" % (run, dict(c)))

print("\n=== 异常 run 里 4/13 的 (idx, X) 序列 ===")
for run, idx, x in sorted(data[(4, 13)], key=lambda t: (t[0], t[1] if isinstance(t[1], int) else 0)):
    if run == "ONCE_20261029_143736":
        print("   idx=%-4s X=%d" % (idx, x))

print("\n=== 4/13 与 4/4 是否共享 X (按 run，统计同 run 内的配对) ===")
byrun13 = collections.defaultdict(set)
byrun4 = collections.defaultdict(set)
for run, idx, x in data[(4, 13)]:
    byrun13[run].add(x)
for run, idx, x in data[(4, 4)]:
    byrun4[run].add(x)
same = 0
diff = []
for run in byrun13:
    s13 = byrun13[run]
    s4 = byrun4.get(run, set())
    if s13 == s4:
        same += 1
    else:
        diff.append((run, sorted(s13), sorted(s4)))
print("  同 run 内 X 集合相同的 run 数=%d, 不同的=%d" % (same, len(diff)))
for d in diff[:6]:
    print("    %s  4/13=%s  4/4=%s" % d)

print("\n=== 932 是否出现在别的 svc/task 的其它位置 ===")
loc = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes) and len(v) == 4 and int.from_bytes(v, "little") == 932:
            loc[(r["svc"], r["task"], i)] += 1
for k, n in loc.most_common():
    print("   svc=%d task=%d elem#%d  x%d" % (k + (n,)))
