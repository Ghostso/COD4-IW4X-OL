# -*- coding: utf-8 -*-
"""打印 C# 参考实现的购买应答构造(第 1328-1348 行)。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "_ref", "CodolLocalLobbyServer.cs")


def main():
    ls = open(P, "r", encoding="utf-8", errors="replace").read().splitlines()
    for a, b in ((1328, 1349),):
        for i in range(a, b):
            print("%5d| %s" % (i + 1, ls[i].rstrip()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
