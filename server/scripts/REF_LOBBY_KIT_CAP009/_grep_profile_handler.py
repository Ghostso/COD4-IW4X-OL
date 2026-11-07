# -*- coding: utf-8 -*-
"""找 lobby_server.py 里 service=8 的处理。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "lobby_server.py")


def main():
    lines = open(P, "r", encoding="utf-8", errors="replace").read().splitlines()
    idx = [i for i, l in enumerate(lines)
           if ("service == 8" in l or "service in (8" in l
               or "public.result" in l or "secure.result" in l
               or "profile" in l.lower())]
    print("命中 %d 行" % len(idx))
    for i in idx:
        lo = max(0, i - 3)
        hi = min(len(lines), i + 8)
        print("=" * 70)
        for j in range(lo, hi):
            print("%5d| %s" % (j + 1, lines[j]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
