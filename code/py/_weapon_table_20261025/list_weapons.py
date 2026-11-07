# -*- coding: utf-8 -*-
"""List type-28 (weapon) assets of an inflated CODOL zone in directory order."""
import struct, sys, io, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\common_mp.zone'
DIR_OFF, DIR_COUNT = 0xFC24, 8557
ASSET_BASE = 0x28
KEY_RE = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
NAME_RE = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_NAME')

d = open(ZONE, 'rb').read()
rows = []
for i in range(DIR_COUNT):
    typ, off, ptr, size = struct.unpack_from('<4I', d, DIR_OFF + i * 16)
    if typ != 28:
        continue
    b = d[ASSET_BASE + off: ASSET_BASE + off + size]
    m = KEY_RE.search(b)
    if m:
        nm = m.group(1).decode('ascii').lower() + '_mp'
    else:
        m = NAME_RE.search(b)
        nm = m.group(1).decode('ascii').lower() if m else None
    rows.append((i, nm, size))

print('type28 total', len(rows))
for i, nm, size in rows[:20]:
    print(i, nm, size)

target = 'm4a1tech_mp'
pos = [k for k, (i, nm, s) in enumerate(rows) if nm == target]
print('positions (0-based within type28 order) of', target, pos)
