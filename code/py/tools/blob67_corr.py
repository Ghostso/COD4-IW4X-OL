#!/usr/bin/env python3
"""67B blob 尾段与同报文其它字段的相关性 + 28/4 结构确认。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

rows = []
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for j, (t, v) in enumerate(els):
        if t == 0x13 and isinstance(v, bytes) and len(v) == 67:
            rows.append((r["svc"], r["task"], r["idx"], v, els, j))

print("=== 尾段 [60..66] 与 同报文 u64(0x0a) / i32 序列 的相关性（21/1 前 12 条）===")
n = 0
for s, t, idx, v, els, j in rows:
    if (s, t) != (21, 1):
        continue
    u64 = [vv for tt, vv in els if tt == 0x0A and isinstance(vv, bytes)]
    i32 = [int.from_bytes(vv, "little", signed=True) for tt, vv in els if tt == 0x07 and isinstance(vv, bytes)]
    print("  idx=%-4d tail=%s  u64=%s  i32[0:4]=%s" % (
        idx, v[60:67].hex(" "), [x.hex() for x in u64], i32[:4]))
    n += 1
    if n >= 12:
        break

print("\n=== 28/4 原始结构 ===")
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    b = bytes.fromhex(r["payload"])
    print("len=%d" % len(b))
    print(b[:120].hex(" "))
    good, els, why = G.parse(b)
    print("good=%s" % good)
    if good:
        for t, v in els[:8]:
            print("  tag %02x %s" % (t, v.hex() if isinstance(v, bytes) else v))
    break

# 28/4 中 00 ff 00 的位置
print("\n=== 28/4 中 00ff00 出现位置（前 5 条）===")
cnt = 0
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    b = bytes.fromhex(r["payload"])
    pos = [i for i in range(1, len(b) - 1) if b[i] == 0xFF and b[i - 1] == 0 and b[i + 1] == 0]
    print("  idx=%-4d len=%-4d 位置=%s" % (r["idx"], len(b), pos[:20]))
    cnt += 1
    if cnt >= 5:
        break
