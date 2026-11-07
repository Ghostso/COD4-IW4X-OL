# -*- coding: utf-8 -*-
"""Is the weapon name the FIRST field of the zone type-28 asset, inline?

If so, the asset bytes begin with the NUL-terminated weapon name and the
SF_WEAPON_<NAME>_MP_NAME localize key sits somewhere further in.
"""
import struct, re, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

d = open(r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\common_mp.zone', 'rb').read()
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')

for i in range(8557):
    typ, off, ptr, size = struct.unpack_from('<4I', d, 0xFC24 + i * 16)
    if typ != 28:
        continue
    b = d[0x28 + off: 0x28 + off + size]
    m = KEY.search(b)
    if not m or m.group(1) != b'M4A1TECH':
        continue
    print('dir index', i, 'size', size)
    for k in range(0, 96, 16):
        row = b[k:k + 16]
        print(' %04x' % k, ' '.join('%02x' % x for x in row).ljust(48),
              ''.join(chr(x) if 32 <= x < 127 else '.' for x in row))
    print(' key at', hex(m.start()))
    # first NUL-terminated token at offset 0?
    e = b.find(b'\0', 0, 64)
    print(' first token:', b[:e])
    break
