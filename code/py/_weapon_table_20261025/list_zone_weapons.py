# -*- coding: utf-8 -*-
"""List type-28 weapon assets of a zone in directory order, with their name."""
import struct, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1]
DIR_OFF = int(sys.argv[2], 0)
DIR_COUNT = int(sys.argv[3], 0)
ASSET_BASE = 0x28
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
NAME = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_NAME')

d = open(ZONE, 'rb').read()
rows = []
for i in range(DIR_COUNT):
    t, off, ptr, sz = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if t != 28:
        continue
    b = d[ASSET_BASE + off: ASSET_BASE + off + sz]
    m = KEY.search(b)
    nm = m.group(1).decode().lower() + '_mp' if m else (
        NAME.search(b).group(1).decode().lower() if NAME.search(b) else '?')
    rows.append((i, nm, sz))

print('type28 count', len(rows))
for k, (i, nm, sz) in enumerate(rows):
    print('  %3d  dir=%-5d %-28s size=%d' % (k, i, nm, sz))

for probe in ('m4a1tech_mp', 'fa1911ncm_mp', 'm4_mp', 'ak47_mp', 'cheytac_mp'):
    print(probe, [k for k, (i, n, s) in enumerate(rows) if n == probe])
