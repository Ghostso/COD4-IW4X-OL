#!/usr/bin/env python3
"""6/14 blob 内层结构：4 字节长度前缀 + 命令串；mmbook vs mmstart 的完整清单。"""
import collections
import json
import re
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

rows = []
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x13 and isinstance(v, bytes):
            rows.append((r["idx"], v))
            break

print("6/14 blob 样本 %d 个" % len(rows))

# 1) 首 4 字节是否 == len(其余)
ok = 0
pref = collections.Counter()
for idx, v in rows:
    if len(v) >= 4:
        n = struct.unpack("<I", v[:4])[0]
        pref[(n == len(v) - 4)] += 1
print("首 4 字节 u32 == len(blob)-4 的比例: %s" % dict(pref))

# 2) 命令词统计
cmds = collections.Counter()
for idx, v in rows:
    s = v[4:].decode("latin1") if len(v) > 4 else ""
    m = re.match(r"^([a-zA-Z_]+)", s)
    cmds[m.group(1) if m else "?"] += 1
print("\n首 4 字节之后的命令词:")
for k, v in cmds.most_common():
    print("  %-14s : %d" % (k, v))

# 3) mmbook 的完整清单（去重）
print("\n=== mmbook 命令去重 top10 ===")
mb = collections.Counter()
for idx, v in rows:
    s = v[4:].decode("latin1") if len(v) > 4 else ""
    if s.startswith("mmbook"):
        mb[s] += 1
for k, v in mb.most_common(10):
    print("  x%-4d %r" % (v, k[:160]))

# 4) mmstart 的完整清单（去重）
print("\n=== mmstart 命令去重 top6 ===")
ms = collections.Counter()
for idx, v in rows:
    s = v[4:].decode("latin1") if len(v) > 4 else ""
    if s.startswith("mmstart"):
        ms[s] += 1
for k, v in ms.most_common(6):
    print("  x%-4d %r" % (v, k[:300]))

# 5) 29 字节样本是否完全一致
print("\n=== 29 字节样本的不同取值 ===")
d = collections.Counter(v for idx, v in rows if len(v) == 29)
for k, v in d.most_common(5):
    print("  x%-4d %r" % (v, k.decode("latin1")))
