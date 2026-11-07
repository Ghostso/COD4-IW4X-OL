# -*- coding: utf-8 -*-
"""Dump a small stringtable asset raw, to learn the cell/string layout."""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'
DIR_OFF, DIR_COUNT = 0x926, 901
ASSET_BASE = 0x28

d = open(ZONE, 'rb').read()
for idx in (791, 885, 813, 802):
    typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + idx * 16)
    start = ASSET_BASE + off
    blob = d[start:start + size]
    cols, rows = struct.unpack_from('<II', blob, 4)
    print('=== idx', idx, 'size', size, 'cols', cols, 'rows', rows)
    for k in range(0, min(len(blob), 320), 16):
        row = blob[k:k + 16]
        print(' %04x' % k, ' '.join('%02x' % b for b in row).ljust(48),
              ''.join(chr(b) if 32 <= b < 127 else '.' for b in row))
    print()
