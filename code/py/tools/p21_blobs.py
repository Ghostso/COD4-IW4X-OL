#!/usr/bin/env python3
"""21/12 #00 的 0x13 blob（内容=1234605616436508552 的 8 字节？）；21/1 #13 16B blob 是否每 run 变。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("=== 21/12 #00 blob 内容（前 5）===")
n = 0
for r in corpus:
    if (r["svc"], r["task"]) != (21, 12):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    t, v = els[0]
    print("  0x%02x len=%d hex=%s  u64le=%d" % (t, len(v), v.hex(), int.from_bytes(v[:8], "little")))
    n += 1
    if n >= 5:
        break

print("\n=== 21/1 #13 的 16B blob 是否每 run 不同 ===")
c = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (21, 1):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) == 16:
            c[v.hex()] += 1
print("  distinct=%d" % len(c))
for k, n in c.most_common(10):
    print("   %s x%d" % (k, n))

print("\n=== 21/12 #15 的 16B blob ===")
c = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (21, 12):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes) and len(v) == 16:
            c[v.hex()] += 1
print("  distinct=%d" % len(c))
for k, n in c.most_common(10):
    print("   %s x%d" % (k, n))

# 21/1 #14 255 vs 0 与 #18 大值 的关系（同一 run 内）
print("\n=== 21/1 #14=255 的 run vs #24 != B 的 run ===")
for r in corpus:
    if (r["svc"], r["task"]) != (21, 1):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    v14 = int.from_bytes(els[14][1], "little", signed=True) if els[14][0] == 0x07 else None
    v24 = int.from_bytes(els[24][1], "little", signed=True) if els[24][0] == 0x07 else None
    v19 = int.from_bytes(els[19][1], "little", signed=True) if els[19][0] == 0x07 else None
    print("  run=%s  #14=%s #19=%s #24=%s" % (r.get("run"), v14, v19, v24))
