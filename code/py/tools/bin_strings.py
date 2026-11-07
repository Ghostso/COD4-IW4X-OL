#!/usr/bin/env python3
"""列出二进制里的可打印 ASCII / UTF-16LE 字符串（含偏移），支持过滤。"""
import re
import sys


def main():
    path = sys.argv[1]
    pat = sys.argv[2] if len(sys.argv) > 2 else None
    minlen = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    b = open(path, "rb").read()

    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, b):
        s = m.group()
        if pat and pat.lower() not in s.decode("latin1").lower():
            continue
        print("%#08x  %s" % (m.start(), s.decode("latin1")[:160]))


if __name__ == "__main__":
    main()
