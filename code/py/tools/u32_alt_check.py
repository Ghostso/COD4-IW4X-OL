#!/usr/bin/env python3
"""关键复核：1800154382 是否 = 账号 ID 的低 32 位（0x6B4C2D0E）？
   以及 11/4 里它出现的完整报文上下文。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

ACC = 0xE7C8A98A6B4C2D0E
ALT = 1800154382
print("账号 ID = 0x%016X" % ACC)
print("低 32 位 = 0x%08X = %d" % (ACC & 0xFFFFFFFF, ACC & 0xFFFFFFFF))
print("高 32 位 = 0x%08X = %d" % (ACC >> 32, ACC >> 32))
print("1800154382 = 0x%08X  ->  等于低32位? %s" % (ALT, (ACC & 0xFFFFFFFF) == ALT))
print("0x6B4E6E0E = %d （我上一版论文写的 hex 是否正确? %s）" % (0x6B4E6E0E, 0x6B4E6E0E == ALT))
print("0x6B4C2D0E = %d （正确 hex? %s）" % (0x6B4C2D0E, 0x6B4C2D0E == ALT))

# 11/4 里 u64 == ALT 的报文全文
print("\n=== 11/4 中 u64 == 1800154382 的完整报文（前 3 条）===")
n = 0
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    hit = any(t == 0x0A and isinstance(v, bytes) and len(v) == 8
              and int.from_bytes(v, "little") == ALT for t, v in els)
    if not hit:
        continue
    print("  run=%s len=%d" % (r.get("run"), len(b)))
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
            print("    #%02d 0x%02x = %d (0x%X)" % (i, t, int.from_bytes(v, "little"), int.from_bytes(v, "little")))
        elif isinstance(v, bytes):
            print("    #%02d 0x%02x len=%d %s" % (i, t, len(v), v[:24].hex()))
        else:
            print("    #%02d 0x%02x %r" % (i, t, v))
    n += 1
    if n >= 3:
        break

# 11/4 里所有 u64 值（不只 54 种值里的）
print("\n=== 11/4 的 u64 取值分布 ===")
c = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (11, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x0A and isinstance(v, bytes) and len(v) == 8:
            c[int.from_bytes(v, "little")] += 1
for k, n in c.most_common(10):
    print("  %d (0x%X) x%d" % (k, k, n))

# 21/1、21/12、11/2 里 ALT 的位置
for svc, task in [(21, 1), (21, 12), (11, 2)]:
    print("\n=== %d/%d 中 ALT 的位置 ===" % (svc, task))
    pos = collections.Counter()
    for r in corpus:
        if (r["svc"], r["task"]) != (svc, task):
            continue
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes) and len(v) == 8 and int.from_bytes(v, "little") == ALT:
                pos[(i, len(els))] += 1
    for k, n in pos.most_common(5):
        print("  元素#%d/%d x%d" % (k[0], k[1], n))
