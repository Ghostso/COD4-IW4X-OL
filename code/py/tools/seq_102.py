#!/usr/bin/env python3
"""102/1 与 102/5 的元素序列（0x03 取 2/3 的语境）。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
want = [(102, 1), (102, 5), (102, 7), (68, 3)]
for w in want:
    seen = 0
    for r in corpus:
        if (r["svc"], r["task"]) != w:
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        seq = []
        for t, v in els:
            if isinstance(v, bytes):
                if len(v) <= 2:
                    seq.append("%02x=%s" % (t, v.hex()))
                else:
                    seq.append("%02x[%dB]" % (t, len(v)))
            else:
                seq.append("%02x=%r" % (t, v))
        print("%d/%d len=%d: %s" % (w[0], w[1], len(b), " ".join(seq)))
        seen += 1
        if seen >= 3:
            break
    print()
