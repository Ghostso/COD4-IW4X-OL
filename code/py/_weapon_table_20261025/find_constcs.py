# -*- coding: utf-8 -*-
"""Locate mp/constconfigstrings_*.csv stringtables inside an inflated CODOL zone."""
import struct, sys, io, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1] if len(sys.argv) > 1 else r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\code_post_gfx_mp.zone'

d = open(ZONE, 'rb').read()
print('zone bytes', len(d))

for pat in (b'mp/constconfigstrings_mp.csv', b'mp/constconfigstrings_coop.csv',
            b'mp/constconfigstrings_zm.csv'):
    offs = []
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        offs.append(i)
        i += 1
    print(pat, [hex(o) for o in offs])

# Print context around the first hit of mp csv
i = d.find(b'mp/constconfigstrings_mp.csv')
if i >= 0:
    start = max(0, i - 96)
    ctx = d[start:i + 64]
    for k in range(0, len(ctx), 16):
        row = ctx[k:k + 16]
        hexs = ' '.join('%02x' % c for c in row)
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)
        print(hex(start + k), hexs.ljust(48), asc)
