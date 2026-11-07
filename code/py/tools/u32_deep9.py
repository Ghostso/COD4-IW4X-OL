#!/usr/bin/env python3
"""0x08 深挖九：21/5、6/5、3/46、3/48、29/10、102/1 的 u32 语义（分页/上限类）。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("=== 21/5 全序列（前 2 条）===")
seen = 0
for r in corpus:
    if (r["svc"], r["task"]) != (21, 5):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    parts = []
    for t, v in els:
        if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
            parts.append("0x%02x=%d" % (t, int.from_bytes(v, "little", signed=(t == 0x07))))
        elif isinstance(v, bytes):
            esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
            parts.append("0x%02x[%d]=%s" % (t, len(v), esc))
        else:
            parts.append("0x%02x=%r" % (t, v))
    print("   len=%d : %s" % (len(b), " | ".join(parts)))
    seen += 1
    if seen >= 2:
        break

# 21/5 各位置 distinct
print("\n=== 21/5 各 u32 位置 distinct ===")
pos = collections.defaultdict(collections.Counter)
for r in corpus:
    if (r["svc"], r["task"]) != (21, 5):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    j = 0
    for i, (t, v) in enumerate(els):
        if t == 0x08 and len(v) == 4:
            pos[j][int.from_bytes(v, "little")] += 1
            j += 1
for k, c in sorted(pos.items()):
    print("  u32#%d distinct=%d top=%s" % (k, len(c), c.most_common(5)))

# 6/5
print("\n=== 6/5 各 u32 位置 distinct ===")
pos = collections.defaultdict(collections.Counter)
for r in corpus:
    if (r["svc"], r["task"]) != (6, 5):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    j = 0
    for i, (t, v) in enumerate(els):
        if t == 0x08 and len(v) == 4:
            pos[j][int.from_bytes(v, "little")] += 1
            j += 1
for k, c in sorted(pos.items()):
    print("  u32#%d distinct=%d top=%s" % (k, len(c), c.most_common(5)))

# 102/1
print("\n=== 102/1 各 u32 位置 distinct ===")
pos = collections.defaultdict(collections.Counter)
for r in corpus:
    if (r["svc"], r["task"]) != (102, 1):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    j = 0
    for i, (t, v) in enumerate(els):
        if t == 0x08 and len(v) == 4:
            pos[j][int.from_bytes(v, "little")] += 1
            j += 1
for k, c in sorted(pos.items()):
    print("  u32#%d distinct=%d top=%s" % (k, len(c), c.most_common(5)))
