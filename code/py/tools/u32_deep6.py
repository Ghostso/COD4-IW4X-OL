#!/usr/bin/env python3
"""0x08 深挖六：80/119 #3 全值；71/4 的 u32 是否 MAC 哈希；0x3a4/0x3ec 语义。"""
import collections
import hashlib
import json
import struct
import sys
import zlib

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

print("=== 80/119 元素#3 全值 ===")
c = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (80, 119):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    u = [int.from_bytes(v, "little") for t, v in els if t == 0x08 and len(v) == 4]
    if len(u) >= 4:
        c[u[3]] += 1
print("  n=%d distinct=%d" % (sum(c.values()), len(c)))
for k, n in c.most_common(10):
    print("    %-12d 0x%08x x%d" % (k, k, n))

# 71/4 的 u32 vs MAC 哈希
mac = "D4-93-90-18-55-10"
target = 31902622
print("\n=== 31902622 vs MAC 哈希候选 ===")
print("  target = 0x%08X" % target)
cands = {}
for name, data in [("mac_str", mac.encode()), ("mac_hex", b"D49390185510"),
                   ("mac_colon", b"D4:93:90:18:55:10"), ("mac_raw", bytes.fromhex("D49390185510"))]:
    cands["crc32_" + name] = zlib.crc32(data) & 0xFFFFFFFF
    cands["md5lo_" + name] = int.from_bytes(hashlib.md5(data).digest()[:4], "little")
    cands["md5be_" + name] = int.from_bytes(hashlib.md5(data).digest()[:4], "big")
    cands["sha1lo_" + name] = int.from_bytes(hashlib.sha1(data).digest()[:4], "little")
for k, v in cands.items():
    mark = " <<< MATCH" if v == target else ""
    print("  %-20s 0x%08X%s" % (k, v, mark))

# 31902622 的其它解释
print("\n=== 31902622 其它解释 ===")
print("  0x%08X  low16=0x%04X high16=0x%04X" % (target, target & 0xFFFF, target >> 16))
print("  as date(2000-01-01 epoch): n/a (太大)")

# 4/13 的 #0 非 932 值 是不是 0x64 起的枚举
print("\n=== 4/13 #0 值清单（按 run）===")
per_run = collections.defaultdict(collections.Counter)
for r in corpus:
    if (r["svc"], r["task"]) != (4, 13):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    if els and els[0][0] == 0x08:
        per_run[r.get("run")][int.from_bytes(els[0][1], "little")] += 1
for run, cnt in sorted(per_run.items()):
    if any(v != 932 for v in cnt):
        print("  %s -> %s" % (run, dict(cnt)))
