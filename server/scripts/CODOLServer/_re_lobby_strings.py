# -*- coding: utf-8 -*-
"""Dump all lobby/blaze/logon/url strings from codoMP_client_shipRetailBase.dll."""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DLL = os.path.join(PROJECT, 'COD OL', 'codoMP_client_shipRetailBase.dll')
OUT = os.path.join(HERE, '_re_lobby_strings.txt')

KEYWORDS = (
    'lobby', 'blaze', 'demonware', 'dwlogon', 'dwlobby', 'logon',
    'umbrella', 'title_id', 'onlinegame', 'stun.', 'natserver',
    'matchmaking', 'presence', 'bd_', 'dw_',
)


def ascii_strings(data, min_len=4):
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % min_len, data):
        yield m.start(), m.group().decode('ascii', 'replace')


def utf16_strings(data, min_len=4):
    # ASCII characters separated by NUL
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}' % min_len, data):
        s = m.group().decode('utf-16le', 'replace')
        yield m.start(), s


def main():
    data = open(DLL, 'rb').read()
    lines = []
    lines.append('file %s size=%d' % (DLL, len(data)))
    lines.append('')

    for label, gen in (('ASCII', ascii_strings(data)), ('UTF16', utf16_strings(data))):
        lines.append('=' * 100)
        lines.append('%s strings containing keyword' % label)
        lines.append('=' * 100)
        seen = set()
        for off, s in gen:
            low = s.lower()
            if not any(k in low for k in KEYWORDS):
                continue
            if s in seen:
                continue
            seen.add(s)
            if len(seen) > 600:
                break
            lines.append('  off=0x%08X  %r' % (off, s))
        lines.append('  count=%d' % len(seen))
        lines.append('')

    # Also: all dotted hostnames of shape *.demonware.net / *.qq.com / *.callofduty.com
    lines.append('=' * 100)
    lines.append('hostname-like strings')
    lines.append('=' * 100)
    seen = set()
    for off, s in ascii_strings(data, 6):
        low = s.lower()
        if re.search(r'[a-z0-9\-]+(\.[a-z0-9\-]+)+', low) and any(
                d in low for d in ('demonware', 'callofduty', 'activision', 'qq.com', 'lobby')):
            if s in seen:
                continue
            seen.add(s)
            lines.append('  off=0x%08X  %r' % (off, s))
    for off, s in utf16_strings(data, 6):
        low = s.lower()
        if re.search(r'[a-z0-9\-]+(\.[a-z0-9\-]+)+', low) and any(
                d in low for d in ('demonware', 'callofduty', 'activision', 'qq.com', 'lobby')):
            if s in seen:
                continue
            seen.add(s)
            lines.append('  off=0x%08X  %r' % (off, s))
    lines.append('  count=%d' % len(seen))

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)
    print('lines', len(lines))
    for ln in lines[:200]:
        print(ln)


if __name__ == '__main__':
    main()
