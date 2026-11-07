#!/usr/bin/env python3
"""0x6b / 0x6c 数组全语料普查：出现次数、task 分布、元素字节长度、count 与 body 关系。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

stat = {0x6B: collections.Counter(), 0x6C: collections.Counter()}
bytask = {0x6B: collections.defaultdict(collections.Counter),
          0x6C: collections.defaultdict(collections.Counter)}
total = {0x6B: 0, 0x6C: 0}
samples = {0x6B: [], 0x6C: []}
cnt_body = {0x6B: collections.Counter(), 0x6C: collections.Counter()}

for r in corpus:
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t not in (0x6B, 0x6C):
            continue
        total[t] += 1
        cnt, body = v
        stat[t][len(body)] += 1
        bytask[t][(r["svc"], r["task"])][len(body)] += 1
        # count 与 body 的关系
        rel = None
        if len(body) == 0:
            rel = "empty"
        elif cnt == 0:
            rel = "cnt0_body%d" % len(body)
        elif len(body) % cnt == 0:
            rel = "divisible:%d" % (len(body) // cnt)
        else:
            rel = "nondiv:%d/%d" % (len(body), cnt)
        cnt_body[t][rel] += 1
        if len(samples[t]) < 6:
            samples[t].append((r["svc"], r["task"], cnt, len(body), body[:48].hex()))

for t in (0x6B, 0x6C):
    print("\n########## 0x%02X  总数=%d ##########" % (t, total[t]))
    print("body 字节长度分布（前 20）:")
    for k, n in stat[t].most_common(20):
        print("   len=%-5d x%d" % (k, n))
    print("count/body 关系:")
    for k, n in cnt_body[t].most_common(15):
        print("   %-20s x%d" % (k, n))
    print("task 分布:")
    for k, c in sorted(bytask[t].items(), key=lambda x: -sum(x[1].values())):
        tot = sum(c.values())
        lens = ",".join(str(l) for l, _ in c.most_common(5))
        print("   %3d/%-3d x%-5d lens=[%s]" % (k[0], k[1], tot, lens))
    print("样本:")
    for s in samples[t]:
        print("   %d/%d cnt=%d bodylen=%d %s" % s)
