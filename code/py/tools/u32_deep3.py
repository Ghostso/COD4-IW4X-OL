#!/usr/bin/env python3
"""0x08 深挖三：run 名与 0x6cc0 时间戳对齐；932 是否全局唯一头；71/4 全字段。"""
import collections
import datetime
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# run 名清单
runs = collections.Counter(r.get("run") for r in corpus)
print("=== run 数 = %d ===" % len(runs))
for k, n in sorted(runs.items()):
    print("  %-28s %d 条" % (k, n))

# 80/119 的 0x6cc0 时间戳 与 run 名比对
print("\n=== 80/119 时间戳 vs run 名 ===")
for r in corpus:
    if (r["svc"], r["task"]) != (80, 119):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    ts = None
    for t, v in els:
        if t == 0x08 and isinstance(v, bytes) and len(v) == 4:
            iv = int.from_bytes(v, "little")
            if 0x6cc00000 <= iv <= 0x6cc0ffff:
                ts = iv
    if ts:
        local = datetime.datetime.utcfromtimestamp(ts + 8 * 3600)
        print("  run=%-28s ts=%d -> UTC+8 %s" % (r.get("run"), ts, local.strftime("%Y-%m-%d %H:%M:%S")))

# 932 全语料归属
print("\n=== 值 932 (0x3a4) 归属 task ===")
c = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x08 and isinstance(v, bytes) and len(v) == 4 and int.from_bytes(v, "little") == 932:
            c[(r["svc"], r["task"])] += 1
for k, n in c.most_common():
    print("  %d/%d x%d" % (k[0], k[1], n))

# 71/4 全字段（含 latin1 文本）
print("\n=== 71/4 全部样本的元素（前 3 条）===")
seen = 0
for r in corpus:
    if (r["svc"], r["task"]) != (71, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    print("  --- len=%d ---" % len(b))
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes):
            print("   #%02d 0x%02x len=%d hex=%s txt=%r" % (i, t, len(v), v.hex(), v.decode("latin1", "replace")))
        else:
            print("   #%02d 0x%02x %r" % (i, t, v))
    seen += 1
    if seen >= 3:
        break
