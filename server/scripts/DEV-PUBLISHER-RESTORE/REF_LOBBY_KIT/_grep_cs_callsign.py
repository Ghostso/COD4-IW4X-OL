# -*- coding: utf-8 -*-
"""在 C# 参考实现里找名片/Callsign/购买相关的处理。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "_ref", "CodolLocalLobbyServer.cs")


def main():
    lines = open(P, "r", encoding="utf-8", errors="replace").read().splitlines()
    print("文件 %d 行" % len(lines))
    pats = {
        "callsign": re.compile(r"callsign|CallSign", re.I),
        "marketplace": re.compile(r"marketplace|Marketplace"),
        "purchase": re.compile(r"purchase|Purchase"),
        "service80": re.compile(r"\b80\b"),
        "service93": re.compile(r"\b93\b"),
    }
    for name, pat in pats.items():
        idx = [i for i, l in enumerate(lines) if pat.search(l)]
        print()
        print("== %s: %d 行 ==" % (name, len(idx)))
        for i in idx[:25]:
            print("%5d| %s" % (i + 1, lines[i].strip()[:150]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
