#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map GDP command enum values to names using the descriptor table."""

import csv
import os
import struct

PATH = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\GDPOpenProtocol.tdr'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   '..', 'GDP_CMD_MAP.csv')


def cstr(data, off):
    if off <= 0 or off >= len(data):
        return ''
    end = data.find(b'\x00', off)
    if end < 0:
        end = min(len(data), off + 200)
    raw = data[off:end]
    ok = sum(1 for c in raw if 32 <= c < 127)
    if not raw or ok < len(raw) * 0.9:
        return ''
    return raw.decode('ascii', 'replace')


def main():
    data = open(PATH, 'rb').read()
    counts = [struct.unpack_from('<I', data, o)[0]
              for o in (0x24, 0x28, 0x2c, 0x30)]
    print('counts', counts)

    rows = []
    for start, count, label in ((0x194, counts[1], 'A'),
                                (0x194 + counts[1] * 16, counts[2], 'B')):
        for i in range(count):
            off = start + i * 16
            if off + 16 > len(data):
                break
            name_ptr, enum, next_ptr, flag = struct.unpack_from('<IIII',
                                                                data, off)
            # The name usually starts a few bytes before name_ptr.
            name = cstr(data, name_ptr - 24)
            if not name:
                for back in range(0, 40):
                    cand = cstr(data, name_ptr - back)
                    if cand and 'GDP_' in cand:
                        name = cand
                        break
            if not name:
                name = cstr(data, name_ptr)
            if name:
                rows.append({'table': label, 'index': i, 'enum': enum,
                             'name': name, 'off': off})

    print('named entries', len(rows))
    # Show enum order for GDP_CF_* commands.
    cmds = [r for r in rows if 'GDP_CF_' in r['name'] or
            'GDP_DNF_' in r['name'] or 'GDP_BNS_' in r['name']]
    cmds.sort(key=lambda r: r['enum'])
    print('\n=== command enum map (first 80) ===')
    for r in cmds[:80]:
        print('  0x%04X  %s' % (r['enum'], r['name'][:70]))

    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['table', 'index', 'enum', 'name', 'descriptor_off'])
        for r in rows:
            w.writerow([r['table'], r['index'], '0x%04X' % r['enum'],
                        r['name'], '0x%X' % r['off']])
    print('\nwrote', OUT)


if __name__ == '__main__':
    main()
