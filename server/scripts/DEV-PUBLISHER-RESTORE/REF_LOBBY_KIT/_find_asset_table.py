# -*- coding: utf-8 -*-
"""看 0x239B120 这个资源表是什么。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")


def main():
    for fn in sorted(os.listdir(MEM)):
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        try:
            base = int(fn[2:10], 16)
            size = int(fn[11:19], 16)
        except Exception:
            continue
        if not (base <= 0x239B120 < base + size):
            continue
        print("0x239B120 在 %s (base=0x%X size=0x%X)" % (fn, base, size))
        b = open(p, "rb").read()
        off = 0x239B120 - base
        print("文件内偏移 0x%X" % off)
        seg = b[max(0, off - 0x100):off + 0x300]
        for s in re.findall(rb"[ -~]{5,100}", seg):
            print("   %s" % s.decode("latin1"))
        return 0
    print("0x239B120 不在任何已抓区里")
    return 1


if __name__ == "__main__":
    sys.exit(main())
