#!/usr/bin/env python3
"""全语料搜索 c0 a8 55 01（192.168.85.1）与其它私网 IP，并统计 67B blob 尾段。"""
import collections
import json
import sys

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

needle = bytes.fromhex("c0a85501")
hits = collections.Counter()
ip_like = collections.Counter()
tail = collections.Counter()

for r in corpus:
    b = bytes.fromhex(r["payload"])
    k = (r["svc"], r["task"])
    c = b.count(needle)
    if c:
        hits[k] += c
    # 找所有形如 c0 a8 xx xx 的私网 IP
    for i in range(len(b) - 3):
        if b[i] == 0xC0 and b[i + 1] == 0xA8:
            ip_like[(k, "%d.%d.%d.%d" % tuple(b[i:i + 4]))] += 1
    # 67B blob 尾段
    if len(b) >= 6:
        pass

print("=== 192.168.85.1 (c0a85501) 出现次数 ===")
for k, v in hits.most_common(20):
    print("  %d/%d : %d" % (k[0], k[1], v))
print("  合计 %d" % sum(hits.values()))

print("\n=== 所有 c0a8xxxx (192.168.x.x) 私网 IP 及其 task ===")
for k, v in ip_like.most_common(20):
    print("  %d/%d  %s : %d" % (k[0][0], k[0][1], k[1], v))
