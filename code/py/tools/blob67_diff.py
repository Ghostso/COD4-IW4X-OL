#!/usr/bin/env python3
"""67B blob：列出全部不同取值，并标注差异位置。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
groups = collections.defaultdict(collections.Counter)
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) == 67:
            groups[(r["svc"], r["task"])][v] += 1

for k in sorted(groups):
    print("\n=== %d/%d  共 %d 种取值 ===" % (k[0], k[1], len(groups[k])))
    base = groups[k].most_common(1)[0][0]
    print("基线: %s" % base.hex(" "))
    for v, c in groups[k].most_common():
        diffs = [i for i in range(67) if v[i] != base[i]]
        tail = " ".join("%02x" % v[i] for i in range(56, 67))
        print("  x%-3d 差异位=%-22s 尾[56:67]=%s" % (c, str(diffs), tail))
