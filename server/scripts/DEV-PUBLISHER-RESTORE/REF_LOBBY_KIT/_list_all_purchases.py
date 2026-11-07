# -*- coding: utf-8 -*-
"""列出所有购买尝试(成功+失败), 含 SKU 与结果。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    print("所有购买相关行:")
    for i, l in enumerate(lines):
        if ("80/131" in l or "93/131" in l or "80/154" in l or "93/154" in l
                or "购买" in l):
            print("%5d| %s" % (i, l.strip()[:150]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
