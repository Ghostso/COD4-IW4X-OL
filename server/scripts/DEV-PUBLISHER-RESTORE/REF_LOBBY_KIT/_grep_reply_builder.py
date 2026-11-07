# -*- coding: utf-8 -*-
"""找 codol_crypto.py 里的 build_task_reply_objects 实现, 核对 status 字段。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "codol_crypto.py")


def main():
    lines = open(P, "r", encoding="utf-8", errors="replace").read().splitlines()
    idx = [i for i, l in enumerate(lines)
           if "build_task_reply" in l]
    print("命中 %d 行" % len(idx))
    for i in idx:
        lo = max(0, i - 2)
        hi = min(len(lines), i + 30)
        print("=" * 70)
        for j in range(lo, hi):
            print("%5d| %s" % (j + 1, lines[j]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
