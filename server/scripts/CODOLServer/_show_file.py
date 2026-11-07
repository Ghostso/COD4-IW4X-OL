#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print a text file (or a slice of it) with GBK/UTF-8 fallback."""

import sys


def main():
    path = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
    raw = open(path, 'rb').read()
    for enc in ('utf-8', 'gbk', 'latin-1'):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    print(txt[start:start + n])


if __name__ == '__main__':
    main()
