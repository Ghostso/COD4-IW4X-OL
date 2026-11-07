#!/usr/bin/env python3
"""s138_num2id: playlist num(序号) -> playlist id 映射的两种候选(1-based / 0-based 排序下标),
并检验 21/5 的 #02(10/50) 与 21/1 的 #20(123) / mmstart 的 playlist 37 是否一致。
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"
lines = open(P, encoding="latin1").read().splitlines()
ids = []
order = []
for l in lines:
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        ids.append(int(m.group(1)))
        order.append(int(m.group(1)))
srt = sorted(ids)
print("playlist 总数 %d, id 范围 %d..%d" % (len(srt), min(srt), max(srt)))
print("文件顺序前 20:", order[:20])
print("排序后前 20:", srt[:20])


def show(num):
    a = srt[num - 1] if 1 <= num <= len(srt) else None   # 1-based 排序下标
    b = srt[num] if 0 <= num < len(srt) else None        # 0-based
    c = order[num - 1] if 1 <= num <= len(order) else None
    d = order[num] if 0 <= num < len(order) else None
    print("  num=%-4d  1based_sorted=%s 0based_sorted=%s 1based_file=%s 0based_file=%s"
          % (num, a, b, c, d))


for n in (10, 37, 50, 123, 195, 206, 182, 1):
    show(n)
