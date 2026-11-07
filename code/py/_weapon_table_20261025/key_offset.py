# -*- coding: utf-8 -*-
"""WeaponDef asset layout probe: is the name pointer the first dword, and is
the SF_WEAPON_*_MP_NAME localize key always at the same asset offset?"""
import struct, re, io, sys, json, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

d = open(r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\common_mp.zone', 'rb').read()
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')

offs = collections.Counter()
count = 0
for i in range(8557):
    typ, off, ptr, size = struct.unpack_from('<4I', d, 0xFC24 + i * 16)
    if typ != 28:
        continue
    b = d[0x28 + off: 0x28 + off + size]
    m = KEY.search(b)
    if not m:
        continue
    count += 1
    offs[m.start()] += 1

print('type28 assets with a SF_WEAPON_*_MP_NAME key:', count)
for o, c in offs.most_common(6):
    print('  key offset %#x : %d' % (o, c))
