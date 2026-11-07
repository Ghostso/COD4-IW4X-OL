# -*- coding: utf-8 -*-
"""追 1625160 这个版本号在日志/内存里的用法。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    log = os.path.join(ROOT, "lobby_srv.log")
    if os.path.exists(log):
        print("== 日志里含 1625160 的行 ==")
        lines = open(log, "r", encoding="utf-8", errors="replace").read().splitlines()
        for i, l in enumerate(lines):
            if "1625160" in l:
                print("%5d| %s" % (i, l.strip()[:180]))
    print()
    mem = os.path.join(ROOT, "mem_linear")
    print("== 内存里 1625160 的出现 ==")
    for fn in sorted(os.listdir(mem)):
        p = os.path.join(mem, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for nd in (b"1625160",):
            i = b.find(nd)
            if i < 0:
                continue
            print("  %s @0x%X" % (fn, i))
            lo = max(0, i - 60)
            hi = min(len(b), i + 80)
            for s in re.findall(rb"[ -~]{4,70}", b[lo:hi]):
                print("      %s" % s.decode("latin1"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
