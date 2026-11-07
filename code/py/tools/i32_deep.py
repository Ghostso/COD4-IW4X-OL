#!/usr/bin/env python3
"""0x07 i32 深挖：8/3 的 6 值 ID 族、21/1 的 32 值、异常负值的位模式。"""
import collections
import json
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 1) 8/3 的 i32 值域
print("=== 8/3 的 i32 值域（全语料）===")
s83 = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (8, 3):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x07 and isinstance(v, bytes) and len(v) == 4:
            s83[int.from_bytes(v, "little", signed=True)] += 1
for k, v in s83.most_common():
    print("  %-12d (0x%08x) : %d" % (k, k & 0xFFFFFFFF, v))

# 2) 21/1 的 i32 值域
print("\n=== 21/1 的 i32 值域 ===")
s211 = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (21, 1):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x07 and isinstance(v, bytes) and len(v) == 4:
            s211[int.from_bytes(v, "little", signed=True)] += 1
for k, v in s211.most_common():
    print("  %-14d (0x%08x) : %d" % (k, k & 0xFFFFFFFF, v))

# 3) 异常负值的位模式
print("\n=== 异常负值位模式 ===")
for x in [-695030357, -1924013160, 253009291, 1543214545, 1089440719]:
    u = x & 0xFFFFFFFF
    print("  %-14d = 0x%08x  bytes=%s" % (x, u, struct.pack("<i", x).hex(" ")))
