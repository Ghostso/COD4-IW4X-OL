#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan Tenio component DLLs for lobby/auth/server endpoint strings."""

import os
import re

ROOTS = [
    r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\Tenio',
    r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\IIPS\Tenio',
    r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross',
]

TERMS = [
    b'lobby', b'Lobby', b'auth', b'Auth', b'login', b'Login',
    b'loginarea', b'LoginArea', b'server', b'Server', b'host', b'Host',
    b'port', b'Port', b'url', b'Url', b'URL', b'qos', b'Qos', b'tqos',
    b'gdp', b'GDP', b'ticket', b'Ticket', b'sso', b'SSO', b'cross',
    b'store.qq.com', b'intldlgs', b'qq.com',
]


def printable(b):
    return ''.join(chr(c) if 32 <= c < 127 else '.' for c in b)


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'TENIO_COMPONENT_SCAN.txt')
    with open(out, 'w', encoding='utf-8', errors='replace') as fh:
        for root in ROOTS:
            if not os.path.isdir(root):
                continue
            for name in sorted(os.listdir(root)):
                if not name.lower().endswith(('.dll', '.exe', '.ini')):
                    continue
                p = os.path.join(root, name)
                if not os.path.isfile(p) or os.path.getsize(p) > 20_000_000:
                    continue
                data = open(p, 'rb').read()
                hits = {}
                for t in TERMS:
                    n = data.count(t)
                    if n:
                        hits[t.decode('ascii', 'replace')] = n
                if hits:
                    fh.write('\n##### %s (%d) %s\n' % (p, len(data), hits))
                    for t in TERMS:
                        start = 0
                        shown = 0
                        while shown < 5:
                            i = data.find(t, start)
                            if i < 0:
                                break
                            lo = max(0, i - 100)
                            hi = min(len(data), i + 160)
                            fh.write('  [%s] off=0x%X\n    %s\n'
                                     % (t.decode('ascii', 'replace'), i,
                                        printable(data[lo:hi])))
                            start = i + 1
                            shown += 1
    print('wrote', out)


if __name__ == '__main__':
    main()
