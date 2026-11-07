# -*- coding: utf-8 -*-
"""打印最近一次购买的完整往返(请求帧 + 我们的应答)。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    idx = [i for i, l in enumerate(lines)
           if ("80/131" in l or "93/131" in l or "80/154" in l
               or "93/154" in l)]
    if not idx:
        print("没找到购买行")
        return 1
    i = idx[-1]
    lo = max(0, i - 14)
    hi = min(len(lines), i + 14)
    for j in range(lo, hi):
        print("%5d| %s" % (j, lines[j]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
