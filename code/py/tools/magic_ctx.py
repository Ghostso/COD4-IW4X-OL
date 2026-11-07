#!/usr/bin/env python3
"""21/1 与 21/12 完整元素序列（含魔数 A/B 的邻居），判定它们是什么字段。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
A = 0xD692ADAB
B = 0x8D51E398


def dump(svc, task, limit=1):
    print("\n=== %d/%d ===" % (svc, task))
    seen = 0
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        print("  len=%d 元素=%d" % (len(b), len(els)))
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                iv = int.from_bytes(v, "little", signed=(t == 0x07))
                note = ""
                if iv == A:
                    note = "  <<< MAGIC A 0xD692ADAB"
                elif iv == B:
                    note = "  <<< MAGIC B 0x8D51E398"
                print("    #%02d 0x%02x = %d%s" % (i, t, iv, note))
            elif isinstance(v, bytes):
                esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
                print("    #%02d 0x%02x len=%d %s" % (i, t, len(v), esc[:40]))
            else:
                print("    #%02d 0x%02x %r" % (i, t, v))
        seen += 1
        if seen >= limit:
            break


dump(21, 1, 1)
dump(21, 12, 1)
dump(21, 5, 1)
