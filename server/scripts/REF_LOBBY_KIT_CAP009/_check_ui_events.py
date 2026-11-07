# -*- coding: utf-8 -*-
"""看客户端在军牌定制里点购买时, 有没有走 service=6/7/8/102 这类 UI/资产通道。"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    txt = open(LOG, "r", encoding="utf-8", errors="replace").read()
    c = Counter()
    for m in re.finditer(r"service=(\d+) ver=\S+ task=(\d+)", txt):
        c[(int(m.group(1)), int(m.group(2)))] += 1
    print("本次会话的 (service, task) 统计:")
    for (s, t), n in sorted(c.items()):
        print("  %3d/%-4d x%d" % (s, t, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
