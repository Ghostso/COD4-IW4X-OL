# -*- coding: utf-8 -*-
"""列出所有 UNMAPPED 的 (service, task) 及其 payload —— 找名片/Callsign 的查询通道。"""
import os
import re
import struct
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")


def main():
    raw = open(TASKS, "rb").read()
    off = 0
    groups = defaultdict(list)
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        groups[(svc, task)].append(pl)

    print("共 %d 种 (service, task)" % len(groups))
    print()
    for (svc, task) in sorted(groups):
        pls = groups[(svc, task)]
        print("=== %d/%d  x%d" % (svc, task, len(pls)))
        for pl in pls[:3]:
            print("    len=%-5d %s" % (len(pl), pl.hex()[:160]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
