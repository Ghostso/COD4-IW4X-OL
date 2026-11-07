#!/usr/bin/env python3
"""0x08 深挖七：4/13 与 4/4 的元素数分布（是否变长）；异常 run 的完整上下文。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

for svc, task in [(4, 13), (4, 4)]:
    print("\n=== %d/%d 元素数分布 ===" % (svc, task))
    nel = collections.Counter()
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if good:
            nel[len(els)] += 1
    print("  ", dict(nel))

# 4/13 里元素数 >4 的样本（说明有额外 u32）
print("\n=== 4/13 元素数 >4 的样本 ===")
n = 0
for r in corpus:
    if (r["svc"], r["task"]) != (4, 13):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if good and len(els) > 4:
        print("  len=%d run=%s" % (len(b), r.get("run")))
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                print("    #%02d 0x%02x = %d" % (i, t, int.from_bytes(v, "little")))
            elif isinstance(v, bytes):
                print("    #%02d 0x%02x len=%d" % (i, t, len(v)))
            else:
                print("    #%02d 0x%02x %r" % (i, t, v))
        n += 1
        if n >= 3:
            break

# 异常 run 的 4/13 全部记录（按出现顺序）
print("\n=== ONCE_20261029_143736 的 4/13 记录 ===")
for r in corpus:
    if (r["svc"], r["task"]) != (4, 13) or r.get("run") != "ONCE_20261029_143736":
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    print("  idx=%s len=%d : %s" % (r.get("idx"), len(b), b.hex()))
