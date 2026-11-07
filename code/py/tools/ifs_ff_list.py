#!/usr/bin/env python3
"""枚举所有明文清单里出现的 .ff 文件名（去重），并按前缀归类。"""
import os
import re
import sys
from collections import Counter


def main():
    root = sys.argv[1]
    files = sorted(f for f in os.listdir(root) if f.endswith(".ifs"))
    ff = Counter()
    lst = Counter()
    for fn in files:
        p = os.path.join(root, fn)
        with open(p, "rb") as f:
            w = f.read(256 * 1024)
        for m in re.finditer(rb"[A-Za-z0-9_/\\.\-]+\.ff\b", w):
            ff[m.group().decode("latin1")] += 1
        for m in re.finditer(rb"[A-Za-z0-9_/\\.\-]+\.lst\b", w):
            lst[m.group().decode("latin1")] += 1
    print("=== .lst 文件 (%d 个不同) ===" % len(lst))
    for s, n in sorted(lst.items()):
        print("  %-70s x%d" % (s, n))
    print()
    print("=== .ff 文件 (%d 个不同) ===" % len(ff))
    for s, n in sorted(ff.items()):
        print("  %-70s x%d" % (s, n))


if __name__ == "__main__":
    main()
