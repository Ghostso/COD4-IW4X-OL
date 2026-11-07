#!/usr/bin/env python3
"""常量追踪：0xd692adab / 0x8877665544332211 / 0x0e2d4c6b8aa9c8e7 等在全语料的分布。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

needles = {
    "i32 -695030357 (d692adab)": bytes.fromhex("abad92d6"),
    "i32 -1924013160 (8d51e398)": bytes.fromhex("98e3518d"),
    "i32 253009291 (0f149d8b)": bytes.fromhex("8b9d140f"),
    "u64 8877665544332211": bytes.fromhex("1122334455667788"),
    "u64 0e2d4c6b8aa9c8e7": bytes.fromhex("e7c8a98a6b4c2d0e"),
}
hits = {k: collections.Counter() for k in needles}
raw_hits = {k: 0 for k in needles}

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for name, nd in needles.items():
        c = b.count(nd)
        if c:
            raw_hits[name] += c
            hits[name][(r["svc"], r["task"])] += c

for name in needles:
    print("=== %s ===" % name)
    print("  原始字节出现 %d 次" % raw_hits[name])
    for k, v in hits[name].most_common(10):
        print("    %d/%d : %d" % (k[0], k[1], v))
    print()

# 21/1 完整元素序列（带值），看 i32 与 u64 的排列
print("=== 21/1 首个样本完整元素序列 ===")
for r in corpus:
    if (r["svc"], r["task"]) != (21, 1):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for j, (t, v) in enumerate(els):
        if t == 0x13:
            print("  #%02d %02x blob[%d]" % (j, t, len(v)))
        elif t == 0x10:
            print("  #%02d %02x str=%r" % (j, t, v))
        elif t in G.FIXED:
            iv = int.from_bytes(v, "little", signed=(t == 0x07))
            print("  #%02d %02x = %d  (0x%x)" % (j, t, iv, int.from_bytes(v, "little")))
        else:
            print("  #%02d %02x ?" % (j, t))
    break
