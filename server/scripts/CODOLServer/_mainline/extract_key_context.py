#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract large printable context around high-value CODOL runtime strings."""

import argparse
import os
import re

PATTERNS = [
    b'tencent_ticket', b'title_id', b'GameSvrIPList', b'ConndIPPortList',
    b'ConndPort', b'gamesvr', b'qosconnd', b'tqos', b'cod4master',
    b'matchqual', b'newwlobbyinfo', b'hpong', b'BD_TENCENT_NAME_CHANGED',
    b'profiles', b'matchmaking', b'marketplace', b'eventlog',
    b'dwauth.ini', b'stun.ini', b'iips.ini', b'enable_iips',
    b'STUNPingEnabled', b'STUN_STN', b'demonware.net', b'activision.com',
    b'qq.com', b'localhost', b'127.0.0.1',
]


def printable(data):
    return ''.join(chr(c) if 32 <= c < 127 else '\n' if c in (9, 10, 13) else '.'
                   for c in data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bin', required=True)
    ap.add_argument('--base', type=lambda s: int(s, 16), required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--context', type=int, default=2048)
    args = ap.parse_args()

    data = open(args.bin, 'rb').read()
    lines = []
    for pat in PATTERNS:
        start = 0
        n = 0
        while True:
            i = data.find(pat, start)
            if i < 0:
                break
            n += 1
            lo = max(0, i - args.context)
            hi = min(len(data), i + len(pat) + args.context)
            chunk = data[lo:hi]
            lines.append('===== %s hit=%d VA=0x%08X ====='
                         % (pat.decode('ascii', 'replace'), n, args.base + i))
            lines.append(printable(chunk))
            lines.append('')
            start = i + 1
            if n >= 20:
                break
    with open(args.out, 'w', encoding='utf-8', errors='replace') as fh:
        fh.write('\n'.join(lines))
    print('wrote', args.out, 'blocks', len(lines))


if __name__ == '__main__':
    main()
