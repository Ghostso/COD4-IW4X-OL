#!/usr/bin/env python3
"""0xff 的 `00 ff 00` 三重语境解剖：它到底是 u32 的哪一位。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402
import zero_role_census2 as Z  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 收集所有 `00 ff 00` 所在的 8 字节窗口
win = collections.Counter()
task = collections.Counter()
aligned = collections.Counter()
for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    rm = {}
    Z.walk(G.Buf(b), b, rm)
    for i in range(1, len(b) - 1):
        if b[i] == 0xFF and b[i - 1] == 0 and b[i + 1] == 0:
            if rm.get(i) != "B":
                continue
            task[(r["svc"], r["task"])] += 1
            lo = max(0, i - 4)
            win[b[lo:i + 5].hex(" ")] += 1
            # 在 blob 内的相对偏移 mod 4
            j = i
            while j > 0 and rm.get(j - 1) == "B":
                j -= 1
            aligned[(i - j) % 4] += 1

print("=== `00 ff 00` (blob 内) 按 task ===")
for k, v in task.most_common(10):
    print("  %d/%d : %d" % (k[0], k[1], v))
print("\n=== 相对 blob 起点的偏移 mod 4 ===")
for k, v in sorted(aligned.items()):
    print("  mod4=%d : %d" % (k, v))
print("\n=== 9 字节窗口 top10 ===")
for k, v in win.most_common(10):
    print("  %s : x%d" % (k, v))
