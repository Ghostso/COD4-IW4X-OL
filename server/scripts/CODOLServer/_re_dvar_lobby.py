# -*- coding: utf-8 -*-
"""Static hunt for the lobby/Blaze endpoint in the CODOL client binaries.

Looks for:
  1. dvar-style names (dwlobbyhost / blazehost / lobbyhost / onlinegame ...)
  2. IPv4 literals and host:port strings in clear text
  3. Blaze/Demonware hostname patterns
  4. UTF-16LE variants of the same
Dumps surrounding context so we can see default values.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(HERE, '_re_dvar_lobby.txt')

BINARIES = [
    os.path.join(PROJECT, 'COD OL', 'codoMP_client_shipRetail.exe'),
    os.path.join(PROJECT, 'COD OL', 'codoMP_client_shipRetailBase.dll'),
]

DVAR_PATTERNS = [
    b'dwlobbyhost', b'dwlobbyip', b'blazehost', b'blazeip', b'lobbyhost',
    b'lobbyip', b'onlinegame', b'loginserver', b'accountserver',
    b'matchmakingserver', b'titleserver', b'title_id', b'lobbyLandingURL',
    b'demonware', b'blaze', b'dwlogon', b'umbrella',
]

ASCII_IP = re.compile(rb'\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b')
ASCII_HOST = re.compile(rb'\b[a-z0-9](?:[a-z0-9\-]{0,40}[a-z0-9])?'
                        rb'(?:\.[a-z0-9](?:[a-z0-9\-]{0,40}[a-z0-9])?){1,4}\b')


def ctx(data, pos, before=64, after=160):
    lo = max(0, pos - before)
    hi = min(len(data), pos + after)
    return data[lo:hi]


def main():
    lines = []
    for path in BINARIES:
        if not os.path.exists(path):
            lines.append('MISSING %s' % path)
            continue
        data = open(path, 'rb').read()
        name = os.path.basename(path)
        lines.append('=' * 100)
        lines.append('FILE %s  size=%d' % (name, len(data)))
        lines.append('=' * 100)

        for pat in DVAR_PATTERNS:
            hits = []
            start = 0
            while True:
                i = data.find(pat, start)
                if i < 0:
                    break
                hits.append(i)
                start = i + 1
                if len(hits) >= 6:
                    break
            if not hits:
                continue
            lines.append('')
            lines.append('--- pattern %s  hits=%d ---' % (pat.decode('ascii'), len(hits)))
            for i in hits:
                c = ctx(data, i)
                lines.append('  off=0x%08X' % i)
                lines.append('    %s' % repr(c))

        lines.append('')
        lines.append('--- IPv4 literals (unique) ---')
        seen = []
        for m in ASCII_IP.finditer(data):
            s = m.group().decode('ascii')
            if s in seen:
                continue
            seen.append(s)
            if len(seen) <= 80:
                lines.append('  %-22s off=0x%08X  ctx=%s' % (
                    s, m.start(), repr(ctx(data, m.start(), 32, 64))))
        lines.append('  total unique = %d' % len(seen))

        lines.append('')
        lines.append('--- hostname-like tokens with qq/gamesafe/demonware ---')
        seenh = []
        for m in ASCII_HOST.finditer(data):
            s = m.group().decode('ascii', 'replace')
            low = s.lower()
            if not any(k in low for k in ('qq.com', 'demonware', 'blaze', 'gamesafe',
                                          'activision', 'callofduty', 'lobby')):
                continue
            if s in seenh:
                continue
            seenh.append(s)
            if len(seenh) <= 80:
                lines.append('  %-50s off=0x%08X' % (s, m.start()))
        lines.append('  total unique = %d' % len(seenh))
        lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)
    print('lines', len(lines))
    # echo the pattern sections only
    for ln in lines:
        if ln.startswith('---') or ln.startswith('  off=') or ln.startswith('    '):
            print(ln)


if __name__ == '__main__':
    main()
