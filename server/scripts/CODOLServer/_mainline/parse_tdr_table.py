#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse the GDPOpenProtocol.tdr descriptor tables and map command names."""

import struct
import sys

PATH = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\GDPOpenProtocol.tdr'


def cstr(data, off):
    if off <= 0 or off >= len(data):
        return ''
    end = data.find(b'\x00', off)
    if end < 0:
        end = min(len(data), off + 128)
    raw = data[off:end]
    if not raw or any(c < 9 or (13 < c < 32) or c > 126 for c in raw):
        return ''
    return raw.decode('ascii', 'replace')


def main():
    data = open(PATH, 'rb').read()
    print('size=%d magic=0x%08X' %
          (len(data), struct.unpack_from('<I', data, 0)[0]))
    counts = [struct.unpack_from('<I', data, o)[0]
              for o in (0x24, 0x28, 0x2c, 0x30)]
    print('header counts @24/28/2c/30 =', counts)

    # Known descriptor table starts at 0x194. Try 16-byte entries.
    for start, count, label in ((0x194, counts[1], 'tableA'),
                                (0x194 + counts[1] * 16, counts[2], 'tableB'),
                                (0x194 + (counts[1] + counts[2]) * 16,
                                 counts[3], 'tableC')):
        print('\n=== %s start=0x%X count=%d ===' % (label, start, count))
        if start >= len(data):
            print('  out of range')
            continue
        for i in range(min(count, 12)):
            off = start + i * 16
            if off + 16 > len(data):
                break
            a, b, c, d = struct.unpack_from('<IIII', data, off)
            s = cstr(data, a)
            print('  [%3d] @%06X  %08X %08X %08X %08X  %r'
                  % (i, off, a, b, c, d, s[:60]))

    # Map every descriptor entry to its string and look for our commands.
    wanted = [
        'GDP_CF_REQ_ENTERSERVER',
        'GDP_CF_RES_ENTERSERVER',
        'GDP_CF_REQ_SCROLLSERVERLIST',
        'GDP_CF_RES_SCROLLSERVERLIST',
        'GDP_CF_NOTIFY_GAMESERVERPORTINFO',
        'GDP_CF_NOTIFY_LOGIN',
        'GDP_CF_REQ_JOIN_MATCH',
        'GDP_CF_REQ_CREATEROOM',
    ]
    print('\n=== command lookup ===')
    mapping = {}
    for start, count, label in ((0x194, counts[1], 'A'),
                                (0x194 + counts[1] * 16, counts[2], 'B'),
                                (0x194 + (counts[1] + counts[2]) * 16,
                                 counts[3], 'C')):
        for i in range(count):
            off = start + i * 16
            if off + 16 > len(data):
                break
            a, b, c, d = struct.unpack_from('<IIII', data, off)
            s = cstr(data, a)
            if s:
                mapping.setdefault(s, (label, i, off, a, b, c, d))
    for w in wanted:
        print('  %-40s %s' % (w, mapping.get(w, 'NOT_FOUND')))

    # Print all names that look like command/type constants in order.
    print('\n=== first 120 names in table A ===')
    start, count = 0x194, counts[1]
    for i in range(min(count, 120)):
        off = start + i * 16
        a, b, c, d = struct.unpack_from('<IIII', data, off)
        s = cstr(data, a)
        if s:
            print('  [%3d] %-48s size=%X next=%X flag=%X'
                  % (i, s[:48], b, c, d))


if __name__ == '__main__':
    sys.exit(main())
