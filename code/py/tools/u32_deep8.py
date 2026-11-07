#!/usr/bin/env python3
"""0x08 深挖八：80/* 商城族逐 task 元素序列；4/13、4/4 的 #0 跨 run 语义。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def dump(svc, task, limit=1):
    print("\n--- %d/%d ---" % (svc, task))
    seen = 0
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        parts = []
        for t, v in els:
            if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                parts.append("0x%02x=%d" % (t, int.from_bytes(v, "little", signed=(t == 0x07))))
            elif isinstance(v, bytes):
                esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
                parts.append("0x%02x[%d]=%s" % (t, len(v), esc))
            else:
                parts.append("0x%02x=%r" % (t, v))
        print("   len=%d : %s" % (len(b), " | ".join(parts)))
        seen += 1
        if seen >= limit:
            break


for st in [(80, 70), (80, 107), (80, 119), (80, 130), (80, 154), (80, 173), (80, 174), (80, 203), (80, 230), (80, 232), (93, 1), (93, 131)]:
    dump(*st)

# 80 族各 task 的元素数/取值签名
print("\n=== 80/93 族：每个 task 的元素数 + 各位置 distinct ===")
tv = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for r in corpus:
    s, tk = r["svc"], r["task"]
    if s not in (80, 93):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
            tv[(s, tk)][(i, t)][int.from_bytes(v, "little", signed=(t == 0x07))] += 1
for k in sorted(tv):
    print("  %d/%d:" % k)
    for (i, t), c in sorted(tv[k].items()):
        print("     #%02d 0x%02x distinct=%d top=%s" % (i, t, len(c), c.most_common(4)))
