# -*- coding: utf-8 -*-
"""打印本次会话所有购买行(成功+失败), 含 SKU。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    print("日志共 %d 行" % len(lines))
    print()
    for i, l in enumerate(lines):
        if ("购买成功" in l or "购买失败" in l or "Unsupported SKU" in l
                or "marketplace" in l):
            print("%5d| %s" % (i, l.strip()[:160]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
