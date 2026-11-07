# -*- coding: utf-8 -*-
"""看 C# 参考实现的 lsg.log —— 它成功过吗? 购买后客户端要什么?"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "_ref", "lsg.log")


def main():
    if not os.path.exists(LOG):
        print("缺 %s" % LOG)
        return 1
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    print("lsg.log %d 行" % len(lines))
    print()
    # service/task 统计
    c = Counter()
    for l in lines:
        for m in re.finditer(r"(\d+)\s*/\s*(\d+)", l):
            c[(int(m.group(1)), int(m.group(2)))] += 1
    print("(svc/task) 出现次数 top 40:")
    for (s, t), n in c.most_common(40):
        print("  %3d/%-4d x%d" % (s, t, n))
    print()
    for kw in ("PURCHASE", "RAW_", "INVENTORY", "profile", "PROFILE"):
        idx = [i for i, l in enumerate(lines) if kw in l]
        print("== %s: %d 行 ==" % (kw, len(idx)))
        for i in idx[:12]:
            print("  %5d| %s" % (i + 1, lines[i].strip()[:130]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
