#!/usr/bin/env python3
"""11/4 内层结构深解：b0=2 是什么，b1-4 是什么；6/14 DEADC0DE 定位。"""
import collections
import json
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 11/4: 首4B=len, 次1B=?, 再4B=?
print("=== 11/4 blob 内层：b0 与 b1-4 的联合分布 ===")
combo = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) >= 9:
            body = v[4:]
            b0 = body[0]
            u1 = struct.unpack("<I", body[1:5])[0]
            combo[(b0, u1)] += 1
for k, v in combo.most_common(15):
    print("  b0=%-3d u1=%-8d : %d" % (k[0], k[1], v))

# 11/4: b0 的完整取值
print("\n=== 11/4 b0 取值分布 ===")
b0c = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) >= 5:
            b0c[v[4]] += 1
print("  ", dict(b0c.most_common()))

# 11/4: 21B 的那个 blob（b0=0x18=24）
print("\n=== 11/4 的 21B blob（b0=24）全样本 ===")
d = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) == 21:
            d[v.hex()] += 1
for k, v in d.most_common(6):
    print("  x%-3d %s" % (v, k))

# 6/14 DEADC0DE 定位（之前没找到，重查）
print("\n=== 6/14 中 de c0 ad de 的原始位置 ===")
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    i = b.find(bytes.fromhex("dec0adde"))
    if i >= 0:
        print("  len=%d 位置=%d 上下文=%s" % (len(b), i, b[max(0,i-12):i+12].hex(" ")))
        break
