#!/usr/bin/env python3
"""21/5 与 21/12 元素序列 + roomChatChannelID 常量在字符串里的出现。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

for w in [(21, 5), (21, 12)]:
    print("=== %d/%d ===" % w)
    seen = 0
    for r in corpus:
        if (r["svc"], r["task"]) != w:
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        parts = []
        for j, (t, v) in enumerate(els):
            if t == 0x13:
                parts.append("13[%d]" % len(v))
            elif t == 0x10:
                parts.append("10=%r" % v)
            elif t in G.FIXED:
                iv = int.from_bytes(v, "little", signed=(t == 0x07))
                parts.append("%02x=%d" % (t, iv))
            else:
                parts.append("%02x?" % t)
        print("  len=%d: %s" % (len(b), " ".join(parts)))
        seen += 1
        if seen >= 2:
            break
    print()

print("=== 全语料含 'roomChatChannelID' 的字符串 ===")
c = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x10 and isinstance(v, bytes) and b"roomChatChannelID" in v:
            c[(r["svc"], r["task"], v.decode("latin1"))] += 1
for k, v in c.most_common(6):
    print("  %d/%d ×%d: %s" % (k[0], k[1], v, k[2][:200]))

print("\n=== 全语料含 '1234605616436508552' 的位置 ===")
for r in corpus:
    b = bytes.fromhex(r["payload"])
    if b"1234605616436508552" in b:
        print("  %d/%d idx=%s (字符串形式)" % (r["svc"], r["task"], r["idx"]))
        break
