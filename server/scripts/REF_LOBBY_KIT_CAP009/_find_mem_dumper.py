# -*- coding: utf-8 -*-
"""找 mem_linear 是怎么抓的(哪个脚本、什么时机)。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r"mem_linear|_memlinear|dump_region|WriteAllBytes")


def main():
    for f in ("nt10.py", "_dump_all_mem.py", "_dump_mem_linear.py"):
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            print("(缺 %s)" % f)
            continue
        print("=" * 74)
        print("== %s ==" % f)
        lines = open(p, "r", encoding="utf-8", errors="replace").read().splitlines()
        n = 0
        for i, l in enumerate(lines):
            if not PAT.search(l):
                continue
            n += 1
            if n > 6:
                break
            lo = max(0, i - 8)
            hi = min(len(lines), i + 12)
            for j in range(lo, hi):
                print("%5d| %s" % (j + 1, lines[j].rstrip()[:130]))
            print("  ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
