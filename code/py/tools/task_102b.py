#!/usr/bin/env python3
"""102/1 两形态结构 + 102/5 + 102/2 关系。判定 102/1 的 03=3 与 0a 序列。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

for key in [(102, 1), (102, 5), (102, 2)]:
    print("\n########## %d/%d ##########" % key)
    forms = collections.Counter(r["payload"] for r in corpus if (r["svc"], r["task"]) == key)
    for hx, n in forms.most_common():
        b = bytes.fromhex(hx)
        good, els, why = G.parse(b)
        print("  x%-4d len=%d" % (n, len(b)))
        for i, (t, v) in enumerate(els):
            if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
                print("     #%d 0x%02x=%d" % (i, t, int.from_bytes(v, "little", signed=(t == 0x07))))
            elif isinstance(v, bytes):
                print("     #%d 0x%02x[len%d]=%s" % (i, t, len(v), v.hex()))

# 102/1 形态2 的 0a 序列 是否 = 索引
print("\n=== 102/1 形态2 的 03/0a 对序列 ===")
b = bytes.fromhex("0800000000080200000003010a000000000000000003020a000000000000000000")
good, els, why = G.parse(b)
print("els=%d" % len(els))
seq = []
for i, (t, v) in enumerate(els):
    if isinstance(v, bytes) and len(v) in (1, 2, 4, 8):
        seq.append((hex(t), int.from_bytes(v, "little")))
print(seq)

# 102/7 与 102/1 是否同一 08 N 开头模式
print("\n=== 102/7 头部 vs 102/1 头部 ===")
print("102/7: 08 50 = u32 50 (元素数)")
print("102/1 形态1: 08 0 | 08 1 | 03 3 | 0a 0")
print("102/1 形态2: 08 0 | 08 2 | [03 1 | 0a 0] | [03 2 | 0a 0]")
print("=> 102/1 形态2: 08 2 = 元素数2, 后跟 2 组 (03=idx, 0a=val)")
