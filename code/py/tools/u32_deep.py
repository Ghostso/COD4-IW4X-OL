#!/usr/bin/env python3
"""0x08 深挖：0x6cc0 递增簇归哪个 task；31902622(71/4)；932/0x3a4；8/3 的 u32#4。"""
import collections
import json
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 1) 0x6cc0 簇：哪些 task / 报文位置
print("=== 0x6cc0xxxx 簇归属 ===")
c = collections.Counter()
samples = []
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for idx, (t, v) in enumerate(els):
        if t == 0x08 and isinstance(v, bytes) and len(v) == 4:
            iv = int.from_bytes(v, "little")
            if 0x6cc00000 <= iv <= 0x6cc0ffff:
                c[(r["svc"], r["task"])] += 1
                if len(samples) < 5:
                    samples.append((r["svc"], r["task"], idx, len(els), iv))
for k, n in c.most_common():
    print("  %d/%d  x%d" % (k[0], k[1], n))
for s in samples:
    print("  样本 %d/%d 元素#%d/%d = %d (0x%08x)" % (s[0], s[1], s[2], s[3], s[4], s[4]))

# 2) 31902622 in 71/4 — 完整元素序列
print("\n=== 71/4 完整元素序列（第一条）===")
for r in corpus:
    if (r["svc"], r["task"]) != (71, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    print("  len=%d 元素=%d" % (len(b), len(els)))
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes):
            iv = int.from_bytes(v, "little") if len(v) in (1,2,4,8) else None
            print("   #%02d tag=0x%02x len=%d val=%s" % (i, t, len(v), (iv if iv is not None else v.hex())))
        else:
            print("   #%02d tag=0x%02x val=%r" % (i, t, v))
    break

# 3) 932 (0x3a4) 在 4/13 与 4/4 的位置
print("\n=== 值 932 (0x3a4) 的位置分布 ===")
p = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for idx, (t, v) in enumerate(els):
        if t == 0x08 and isinstance(v, bytes) and len(v) == 4:
            if int.from_bytes(v, "little") == 932:
                p[(r["svc"], r["task"], idx, len(els))] += 1
for k, n in p.most_common(10):
    print("  %d/%d 元素#%d/%d  x%d" % (k[0], k[1], k[2], k[3], n))

# 4) 8/3 的 u32 位置 0..3 各自值域
print("\n=== 8/3 前 5 个 u32 的取值 ===")
pos = collections.defaultdict(collections.Counter)
for r in corpus:
    if (r["svc"], r["task"]) != (8, 3):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    u32s = [(i, int.from_bytes(v, "little")) for i, (t, v) in enumerate(els)
            if t == 0x08 and isinstance(v, bytes) and len(v) == 4]
    for j, (i, iv) in enumerate(u32s[:5]):
        pos[j][iv] += 1
for j in range(5):
    print("  u32#%d distinct=%d top=%s" % (j, len(pos[j]), pos[j].most_common(5)))
