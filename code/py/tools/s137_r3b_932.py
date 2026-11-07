#!/usr/bin/env python3
"""s137 R3b: 932 的取值集合 + 上下文相关分析."""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

def els_of(r):
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    return (els if good else None), b

# 每元素位置的值域
for svc, task in ((4, 13), (4, 4)):
    print("=" * 70)
    print("### %d/%d" % (svc, task))
    rows = [r for r in corpus if (r["svc"], r["task"]) == (svc, task)]
    npos = 4
    dist = [collections.Counter() for _ in range(npos)]
    tags = [collections.Counter() for _ in range(npos)]
    combos = collections.Counter()
    for r in rows:
        els, b = els_of(r)
        if not els:
            continue
        vals = []
        for i, (t, v) in enumerate(els):
            tags[i][t] += 1
            iv = int.from_bytes(v, "little") if isinstance(v, bytes) and len(v) in (1, 2, 4, 8) else None
            dist[i][iv] += 1
            vals.append(iv)
        combos[tuple(vals)] += 1
    for i in range(npos):
        top = dist[i].most_common(12)
        print("  elem#%d tags=%s distinct=%d top=%s" % (
            i, dict(tags[i]), len(dist[i]), top))
    print("  --- 全组合 (top):")
    for k, n in combos.most_common(15):
        print("      x%-4d %s" % (n, k))

print("\n" + "=" * 70)
print("### elem#0 == 932 的 run 数量 vs 非 932")
for svc, task in ((4, 13), (4, 4)):
    rows = [r for r in corpus if (r["svc"], r["task"]) == (svc, task)]
    byrun = collections.defaultdict(collections.Counter)
    for r in rows:
        els, b = els_of(r)
        if not els:
            continue
        v0 = int.from_bytes(els[0][1], "little")
        byrun[r.get("run")][v0] += 1
    nonstd = {k: dict(v) for k, v in byrun.items() if set(v) != {932}}
    print("  %d/%d: %d runs, 非全932的 run: %s" % (svc, task, len(byrun), nonstd))

print("\n### 账号/构建相关常量对照")
acct = 0xE7C8A98A6B4C2D0E
print("  账号E7C8A98A6B4C2D0E = %d" % acct)
c = None
for r in corpus:
    if (r["svc"], r["task"]) == (4, 13):
        els, b = els_of(r)
        if els and els[2][0] == 0x0A:
            c = int.from_bytes(els[2][1], "little")
            break
if c is not None:
    print("  4/13 u64(0x0a) 样本 = %d = 0x%016X" % (c, c))
    print("  账号低32位 0x6B4C2D0E = %d" % (acct & 0xFFFFFFFF))
    print("  账号高32位 0xE7C8A98A = %d" % (acct >> 32))
    print("  c 低32 = 0x%08X  c 高32 = 0x%08X" % (c & 0xFFFFFFFF, c >> 32))
    print("  c XOR acct = 0x%016X" % (c ^ acct))
    print("  c - acct = %d" % (c - acct))
    print("  c / 932 = %.6f" % (c / 932))
    print("  c mod 932 = %d" % (c % 932))

print("\n### 932 与已知量算术关系")
vals = {"932": 932, "932*2": 1864, "0x3A4": 0x3A4}
for name, v in vals.items():
    print("  %s = %d" % (name, v))
print("  build 1649370 = 0x%X" % 1649370)
print("  1649370 / 932 = %.3f" % (1649370 / 932))
print("  1649370 %% 932 = %d" % (1649370 % 932))
print("  0x6B4C2D0E & 0xFFFF = %d" % (0x6B4C2D0E & 0xFFFF))
print("  0x6B4C2D0E %% 932 = %d" % (0x6B4C2D0E % 932))
