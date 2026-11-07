# -*- coding: utf-8 -*-
"""看 C# 里 SavePublicProfile 是在哪个 service/task 分支被调用的。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "_ref", "CodolLocalLobbyServer.cs")


def main():
    ls = open(P, "r", encoding="utf-8", errors="replace").read().splitlines()
    for i, l in enumerate(ls):
        if "SavePublicProfile" not in l:
            continue
        print("调用点 @%d: %s" % (i + 1, l.strip()))
        for j in range(i, max(0, i - 80), -1):
            t = ls[j]
            if ("b3 ==" in t or "service ==" in t or "b4 ==" in t
                    or "task ==" in t):
                print("  分支 @%d: %s" % (j + 1, t.strip()[:130]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
