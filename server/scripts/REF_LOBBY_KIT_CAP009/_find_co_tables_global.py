# -*- coding: utf-8 -*-
"""全局找 co* 表名(不要求后面紧跟 zlib), 把位置和上下文都列出来。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
PAT = re.compile(rb"[a-zA-Z0-9_/]{0,24}[Mm]arketplace[A-Za-z0-9_]{0,24}\.csv")


def main():
    hits = {}
    for fn in sorted(os.listdir(MEM)):
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for m in PAT.finditer(b):
            s = m.group(0).decode("latin1")
            hits.setdefault(s, []).append((fn, m.start()))
    print("唯一表名 %d 个:" % len(hits))
    for s in sorted(hits):
        lst = hits[s]
        print("  %-46s %d 处, 首个 %s @0x%X"
              % (s, len(lst), lst[0][0], lst[0][1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
