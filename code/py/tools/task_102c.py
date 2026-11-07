#!/usr/bin/env python3
"""102/7 的 50 个 (03=1, 0a=i) 对：0a 值是否是 0..49 序号。
102/1 形态1: 08 0 | 08 1 | 03 3 | 0a 0 —— 第2字段=1, 第3字段=03 3, 第4=0a 0
102/1 形态2: 08 0 | 08 2 | (03 1,0a 0)(03 2,0a 0)
判定 102/1 的 08=元素数、03=key、0a=val。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 102/7 的 0a 值
print("=== 102/7 的 0a 值序列（前 1 条）===")
for r in corpus:
    if (r["svc"], r["task"]) != (102, 7):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    keys = []
    vals = []
    for i, (t, v) in enumerate(els):
        if t == 0x03:
            keys.append(int.from_bytes(v, "little"))
        elif t == 0x0A:
            vals.append(int.from_bytes(v, "little"))
    print("  03 keys 数=%d 前10=%s" % (len(keys), keys[:10]))
    print("  0a vals 数=%d 前10=%s 后5=%s" % (len(vals), vals[:10], vals[-5:]))
    print("  vals == 0..%d ? %s" % (len(vals)-1, vals == list(range(len(vals)))))
    print("  keys 全=1? %s" % all(k == 1 for k in keys))
    break

# 102/1 形态1 vs 形态2 解读
print("\n=== 102/1 形态1 (08 0 | 08 1 | 03 3 | 0a 0) ===")
print("  假设: 08=fieldA | 08=N(元素数) | [03=key | 0a=val]×N")
print("  形态1: fieldA=0, N=1, 1 对 (key=3, val=0)")
print("  形态2: fieldA=0, N=2, 2 对 (1,0)(2,0)")
print("  => 102/1 = (fieldA=0) + N 个 (key, u64 value) 对")

# 102/5: 08 2 | 03 1 | 03 2 —— 08=2 元素数, 后 2 个 03 值
print("\n=== 102/5 (08 2 | 03 1 | 03 2) ===")
print("  假设: 08=2(元素数) + 2 个 03 值(1, 2) => 索引列表 [1,2]")

# 102/2: 空 00
print("\n=== 102/2: 空(00) ===")
