#!/usr/bin/env python3
"""67 字节 blob 的对齐解剖（21/1、21/12、28/4）。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

blobs = collections.defaultdict(collections.Counter)
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) == 67:
            blobs[(r["svc"], r["task"])][v.hex()] += 1

for k in sorted(blobs):
    tot = sum(blobs[k].values())
    print("\n=== %d/%d : %d 个 67B blob, %d 种不同值 ===" % (k[0], k[1], tot, len(blobs[k])))
    hexs, cnt = blobs[k].most_common(1)[0]
    bb = bytes.fromhex(hexs)
    print("最常见值 (x%d):" % cnt)
    for i in range(0, 67, 16):
        chunk = bb[i:i + 16]
        print("  [%02d] %-47s  %s" % (i, chunk.hex(" "),
              "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)))
