# -*- coding: utf-8 -*-
"""列出日志里出现过的所有 (service, task) 及次数, 找 Callsign 相关通道。"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    c = Counter()
    pat = re.compile(r"解密成功 #\d+ seq=\d+ hmac=\S+ marker=0x\S+ service=(\d+) ver=\S+ task=(\d+)")
    for line in open(LOG, "r", encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            c[(int(m.group(1)), int(m.group(2)))] += 1
    print("共 %d 种 (service, task)" % len(c))
    print()
    for (svc, task), n in sorted(c.items()):
        print("  %3d/%-4d x%d" % (svc, task, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
