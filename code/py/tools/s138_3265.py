#!/usr/bin/env python3
"""s138_3265: 校验 rule 3265 与 vsrule / maxhumanplayersperteam 的关系。
并输出 28/1 tail 与 21/5 playlist 的完整交叉(可选)。
"""
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"
lines = open(P, encoding="latin1").read().splitlines()

blocks = []
cur = None
buf = []
for l in lines:
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        if cur is not None:
            blocks.append((cur, buf))
        cur = int(m.group(1))
        buf = []
    elif cur is not None:
        buf.append(l)
if cur is not None:
    blocks.append((cur, buf))

pair = Counter()
for pid, buf in blocks:
    v = r = None
    for l in buf:
        m1 = re.match(r'^\s*vsrule\s+"?([0-9Vv]+)"?', l)
        if m1:
            v = m1.group(1)
        m2 = re.match(r"^\s*rule\s+3265\s+(\S+)", l)
        if m2:
            r = m2.group(1)
    pair[(v, r)] += 1

print("(vsrule, rule3265) 计数:")
for k, c in sorted(pair.items(), key=lambda x: str(x)):
    print("  %s -> %d" % (k, c))

# 3265 与 vsrule 的总人数换算
print("\n3265 vs 2*vsrule 字段:")
for k, c in sorted(pair.items(), key=lambda x: str(x)):
    v, r = k
    tot = None
    if v:
        nums = re.findall(r"\d+", v)
        if nums:
            tot = 2 * int(nums[-1])
    print("  vsrule=%-6s 3265=%-4s 2*vsrule=%-4s %s  x%d" %
          (v, r, tot, "一致" if str(tot) == str(r) else "", c))
