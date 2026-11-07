# -*- coding: utf-8 -*-
"""打印本轮三笔购买的完整日志上下文。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")


def main():
    lines = open(LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
    print("总行数: %d" % len(lines))
    print()
    idx = [i for i, ln in enumerate(lines)
           if ("购买成功" in ln) or ("80/154" in ln) or ("93/131" in ln)]
    for i in idx:
        lo = max(0, i - 3)
        hi = min(len(lines), i + 3)
        print("-" * 70)
        for j in range(lo, hi):
            print("%4d| %s" % (j, lines[j]))
    print()
    print("=== 末尾 15 行 ===")
    for ln in lines[-15:]:
        print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
