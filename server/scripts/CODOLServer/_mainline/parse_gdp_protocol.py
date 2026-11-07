#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse GDPOpenProtocol.tdr into a command/field index for server work."""

import csv
import os
import re

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
TDR = os.path.join(ROOT, 'GDPOpenProtocol.tdr')
OUT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      '..', 'GDP_PROTOCOL_INDEX.md')
OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'GDP_COMMANDS.csv')


def main():
    data = open(TDR, 'rb').read()
    strings = [m.group().decode('ascii', 'replace')
               for m in re.finditer(rb'[\x20-\x7e]{3,}', data)]
    cmds = []
    types = []
    consts = []
    for s in strings:
        if s.startswith('GDP_CF_') or s.startswith('GDP_DNF_') or \
                s.startswith('GDP_BNS_'):
            cmds.append(s)
        elif re.match(r'^T?GDP[A-Za-z0-9_]+$', s) or \
                re.match(r'^T[A-Z][A-Za-z0-9_]+$', s):
            types.append(s)
        elif s.startswith('MAX_') or s.startswith('GDP_RET_') or \
                re.match(r'^GDP_[A-Z0-9_]+$', s):
            consts.append(s)

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['kind', 'name'])
        for x in cmds:
            w.writerow(['command', x])
        for x in types:
            w.writerow(['type', x])
        for x in consts:
            w.writerow(['constant', x])

    with open(OUT_MD, 'w', encoding='utf-8') as fh:
        fh.write('# GDPOpenProtocol.tdr index\n\n')
        fh.write('source: `%s` (%d bytes, %d strings)\n\n'
                 % (TDR, len(data), len(strings)))
        fh.write('## Commands (%d)\n\n' % len(cmds))
        for x in cmds:
            fh.write('- `%s`\n' % x)
        fh.write('\n## Types (%d)\n\n' % len(types))
        for x in types:
            fh.write('- `%s`\n' % x)
        fh.write('\n## Constants (%d)\n\n' % len(consts))
        for x in consts:
            fh.write('- `%s`\n' % x)
    print('commands=%d types=%d constants=%d' % (len(cmds), len(types),
                                                 len(consts)))
    print('wrote', OUT_MD)
    print('wrote', OUT_CSV)


if __name__ == '__main__':
    main()
