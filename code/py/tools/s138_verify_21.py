#!/usr/bin/env python3
"""138 复核: ①魔数B = crc32("combat")? ②21/1 顺序 c1:11/13 在 21/1 之前?
③playlist num->id 与 21/5 #09 一致性"""
import json
import sys
import zlib
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, encoding="utf-8"))

print("=== ① 魔数 B 是否 = crc32(模式族关键词) ===")
for s in ("combat", "sd", "playlist", "coop", "tdm", "dmz"):
    print("   crc32(%-10s) = 0x%08X" % (s, zlib.crc32(s.encode()) & 0xFFFFFFFF))

print("\n=== ② 建房轮里 11/13 与 21/1 的先后 ===")
runs = {}
for i, r in enumerate(recs):
    runs.setdefault(r["run"], []).append((i, r["svc"], r["task"]))

for run, seq in sorted(runs.items()):
    svcs = [(s, t) for _, s, t in seq]
    if (11, 13) not in svcs:
        continue
    i13 = svcs.index((11, 13))
    i21_1 = svcs.index((21, 1)) if (21, 1) in svcs else None
    flag = ""
    if i21_1 is not None:
        flag = "  >>> 11/13 BEFORE 21/1" if i13 < i21_1 else "  <<< 21/1 BEFORE 11/13"
    print("  %-26s 11/13@%-3d 21/1@%s%s" % (run, i13, i21_1, flag))

print("\n=== ③ 21/5 请求形态抽样 ===")
for r in recs:
    if r["svc"] == 21 and r["task"] == 5:
        p = bytes.fromhex(r["payload"])
        print("  len=%-3d %s" % (len(p), p.hex()[:90]))
        if len(p) > 40:
            break
