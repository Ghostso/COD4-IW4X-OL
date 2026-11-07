#!/usr/bin/env python3
"""21/5 的 0x6b 数组内容；u64 0x1122334455667788 的双形态（二进制 vs 十进制字符串）。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("=== 21/5 完整（含 0x6b 数组内容）===")
n = 0
for r in corpus:
    if (r["svc"], r["task"]) != (21, 5):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    print("  len=%d good=%s" % (len(b), good))
    for j, (t, v) in enumerate(els):
        if t == 0x6B:
            cnt, body = v
            print("    #%d 6b: cnt=%d bodylen=%d body=%s" % (j, cnt, len(body), body.hex(" ")))
        elif isinstance(v, bytes):
            print("    #%d %02x = %s" % (j, t, v.hex(" ")))
        else:
            print("    #%d %02x = %r" % (j, t, v))
    n += 1
    if n >= 1:
        break

print("\n=== u64 0x1122334455667788 的双形态 ===")
bin_cnt = collections.Counter()
str_cnt = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            if int.from_bytes(v, "little") == 0x1122334455667788:
                bin_cnt[(r["svc"], r["task"])] += 1
        if t == 0x10 and isinstance(v, bytes) and b"1234605616436508552" in v:
            str_cnt[(r["svc"], r["task"])] += 1
print("  二进制 u64 0x1122334455667788:", dict(bin_cnt), "合计", sum(bin_cnt.values()))
print("  十进制字符串 '1234605616436508552':", dict(str_cnt), "合计", sum(str_cnt.values()))

print("\n=== 6/14 里含该数字的完整字符串 ===")
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and b"1234605616436508552" in v:
            print("  %r" % v.decode("latin1")[:400])
            sys.exit(0)
