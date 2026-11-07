# -*- coding: utf-8 -*-
"""看客户端 203(库存列表) 请求 payload 里有没有分页/游标参数。"""
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")


def main():
    raw = open(TASKS, "rb").read()
    off = 0
    payloads = Counter()
    n = 0
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) == (80, 203):
            n += 1
            payloads[pl.hex()] += 1
    print("80/203 请求总数: %d" % n)
    print("不同 payload: %d" % len(payloads))
    print()
    for hexs, c in payloads.most_common(12):
        print("  x%-4d %s" % (c, hexs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
