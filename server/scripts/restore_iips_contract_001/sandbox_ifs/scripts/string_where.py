#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
string_where.py -- 在目录树里找出某个字符串（ASCII / UTF-16LE 两种编码）出现在哪些 PE /
文本文件里，用来判断"谁读谁写"。

    python scripts\\string_where.py commonconfig  [--root .] [--min 0]
用法要点：只报"文件 + 偏移"，不做结论。
"""
import argparse
import os
import sys

PE_EXT = ('.exe', '.dll', '.sys', '.ocx', '.tsp')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('needle')
    ap.add_argument('--root', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    ap.add_argument('--pe-only', action='store_true')
    ap.add_argument('--limit', type=int, default=12)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    pats = [('ascii', a.needle.encode('ascii')),
            ('utf16', a.needle.encode('utf-16-le'))]
    hits = 0
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            ext = os.path.splitext(f)[1].lower()
            if a.pe_only and ext not in PE_EXT:
                continue
            if ext not in PE_EXT and ext not in ('.cfg', '.ini', '.xml', '.log', '.tlg', '.tdr', ''):
                continue
            try:
                if os.path.getsize(p) > 260 * 1024 * 1024:
                    continue
                d = open(p, 'rb').read()
            except OSError:
                continue
            for kind, pat in pats:
                at = d.find(pat)
                if at < 0:
                    continue
                offs = []
                while at >= 0 and len(offs) < 5:
                    offs.append(at)
                    at = d.find(pat, at + 1)
                print('%-9s %-70s %s' % (kind, os.path.relpath(p, root),
                                         ' '.join('0x%X' % o for o in offs)))
                hits += 1
                break
    print('--- %d file(s)' % hits)
    return 0


if __name__ == '__main__':
    sys.exit(main())
