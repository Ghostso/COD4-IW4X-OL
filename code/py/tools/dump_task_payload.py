#!/usr/bin/env python3
"""打印 21/1 与 28/4 的 blob 原始字节，定位 ff 00 ff 00 交替区。"""
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
want = (int(sys.argv[2]), int(sys.argv[3]))
shown = 0
for r in corpus:
    if (r["svc"], r["task"]) != want:
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    print("--- %d/%d len=%d good=%s ---" % (r["svc"], r["task"], len(b), good))
    print("hex:", b[:400].hex(" "))
    if good:
        for t, v in els:
            if isinstance(v, bytes):
                print("  tag %02x len=%d: %s" % (t, len(v), v[:200].hex(" ")))
            else:
                print("  tag %02x val=%r" % (t, v))
    shown += 1
    if shown >= 2:
        break
