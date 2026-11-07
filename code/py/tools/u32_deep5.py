#!/usr/bin/env python3
"""0x08 深挖五：4/13 与 4/4 的 #0 非 932 记录；932 语义；0x01E6CB9E 与 MAC。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

for svc, task in [(4, 13), (4, 4)]:
    print("\n=== %d/%d 元素#0 取值分布 + 完整取值组合 ===" % (svc, task))
    c0 = collections.Counter()
    combo = collections.Counter()
    odd = []
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        u = [(t, int.from_bytes(v, "little")) for t, v in els
             if isinstance(v, bytes) and len(v) in (1, 4, 8)]
        c0[u[0][1] if u else None] += 1
        combo[tuple(u)] += 1
        if u and u[0][1] != 932:
            odd.append((r.get("run"), u))
    print("  #0:", dict(c0))
    print("  组合 top5:")
    for k, n in combo.most_common(5):
        print("    %s x%d" % (k, n))
    if odd:
        print("  非 932 记录 %d 条，样例:" % len(odd))
        for o in odd[:5]:
            print("    %s -> %s" % o)

# 71/4 的 MAC 与 u32
print("\n=== 71/4 硬件指纹 ===")
print("  MAC = D4-93-90-18-55-10 (全语料恒定 160/160)")
print("  u32  = 31902622 = 0x%08X (恒定 160/160)" % 31902622)

# 93/1 钱包 / 11/4 / 102/7 的单一常量
print("\n=== 单值 u32 的 task（distinct==1）===")
tv = collections.defaultdict(collections.Counter)
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x08 and isinstance(v, bytes) and len(v) == 4:
            tv[(r["svc"], r["task"])][int.from_bytes(v, "little")] += 1
for k, cnt in sorted(tv.items()):
    if len(cnt) == 1:
        v = list(cnt)[0]
        print("  %d/%-3d  only %-10d x%d" % (k[0], k[1], v, list(cnt.values())[0]))
