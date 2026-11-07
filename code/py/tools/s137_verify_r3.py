#!/usr/bin/env python3
"""137 独立复核 R3: 932 的出现位置/取值集合/两 task 结构."""
import json
import struct
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, encoding="utf-8"))
print("语料记录数 =", len(recs))

# 1) 全语料中 a4 03 00 00 的出现
tot = 0
byoff = Counter()
per = Counter()
vals = Counter()
structs = defaultdict(Counter)
runs_other = []
for r in recs:
    p = bytes.fromhex(r["payload"])
    i = 0
    while True:
        j = p.find(b"\xa4\x03\x00\x00", i)
        if j < 0:
            break
        tot += 1
        byoff[j] += 1
        per[(r["svc"], r["task"])] += 1
        if (r["svc"], r["task"]) in ((4, 13), (4, 4)):
            # elem#0 假设: 偏移 1 = 跟 0x08 标签
            if j == 1 and len(p) >= 5:
                pass
        i = j + 1
print("全语料 '932' 出现 =", tot, " 位置分布 top:", byoff.most_common(3))
print("按 svc/task:", dict(per))

# 2) 4/13 与 4/4 的结构与 elem#0 取值
for svc, task in ((4, 13), (4, 4)):
    rs = [r for r in recs if r["svc"] == svc and r["task"] == task]
    vc = Counter()
    rl = Counter()
    for r in rs:
        p = bytes.fromhex(r["payload"])
        if len(p) >= 5 and p[0] == 0x08:
            vc[struct.unpack_from("<I", p, 1)[0]] += 1
        rl[len(p)] += 1
    print("\n%d/%d : %d 条; 长度分布 %s" % (svc, task, len(rs), dict(rl)))
    print("   elem#0 (偏移1,u32) 取值 =", dict(vc.most_common()))
    r0 = bytes.fromhex(rs[0]["payload"])
    print("   样本0 =", r0.hex())
