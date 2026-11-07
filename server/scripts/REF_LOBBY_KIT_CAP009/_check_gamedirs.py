# -*- coding: utf-8 -*-
"""检查游戏目录里有没有 mp/ main/ 这类散装目录。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.abspath(os.path.join(ROOT, "..", "run_codol_001",
                                    "sandbox_datafix_20260929"))


def main():
    print("游戏目录: %s" % GAME)
    if not os.path.isdir(GAME):
        print("不存在")
        return 1
    top = []
    for n in sorted(os.listdir(GAME)):
        if os.path.isdir(os.path.join(GAME, n)):
            top.append(n)
    print("顶层目录 %d 个:" % len(top))
    for n in top:
        print("   %s" % n)
    print()
    for target in ("mp", "main", "zone", "data"):
        p = os.path.join(GAME, target)
        if not os.path.isdir(p):
            print("  %s/ 不存在" % target)
            continue
        files = os.listdir(p)
        print("%s/ 存在, %d 个条目" % (target, len(files)))
        for f in files[:30]:
            fp = os.path.join(p, f)
            if os.path.isdir(fp):
                kind = "DIR"
            else:
                kind = str(os.path.getsize(fp))
            print("     %-48s %s" % (f, kind))
    return 0


if __name__ == "__main__":
    sys.exit(main())
