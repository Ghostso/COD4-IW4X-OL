# -*- coding: utf-8 -*-
"""打印 service=8 task=3 / 102/2 / 102/5 / 177/29 的 payload —— 新出现的通道。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")
WANT = {(8, 3), (102, 2), (102, 5), (177, 29), (80, 230)}


def main():
    raw = open(TASKS, "rb").read()
    off = 0
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) in WANT:
            print("=== %d/%d  len=%d" % (svc, task, ln))
            print("  hex: %s" % pl.hex())
            # 可打印部分
            s = "".join(chr(c) if 32 <= c < 127 else "." for c in pl)
            print("  asc: %s" % s[:300])
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
