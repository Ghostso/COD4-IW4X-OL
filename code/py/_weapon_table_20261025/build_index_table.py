# -*- coding: utf-8 -*-
"""Build the weapon name <-> engine index table from the inflated 3.19 zone.

Index hypothesis: BG_RegisterWeaponDef appends in the order the weapon assets
appear in the zone XAsset directory (type 28), preceded by the two implicit
definitions. Verified against known runtime ids:
    m4a1tech_mp   -> 1156   (clip 30 / fire 71 in battle_server)
    vector_mp     -> 1157   (clip 36 / fire 59)
    m9gold_mp     -> 1158   (clip 15 / fire 90, semi-auto)
"""
import struct, sys, io, re, json, csv, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\common_mp.zone'
OUT = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
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
        m2 = NAME_RE.search(b)
        nm = m2.group(1).decode('ascii').lower() if m2 else None
    rows.append({'dir_index': i, 'name': nm, 'size': size, 'offset': off})

print('type28 assets:', len(rows))

records = [{'index': 0, 'name': 'none', 'dir_index': None, 'size': None},
           {'index': 1, 'name': 'defaultweapon_mp', 'dir_index': None, 'size': None}]
for k, r in enumerate(rows):
    records.append({'index': k + 2, 'name': r['name'], 'dir_index': r['dir_index'],
                    'size': r['size']})

# checks
probe = {'m4a1tech_mp': 1156, 'vector_mp': 1157, 'm9gold_mp': 1158}
by_name = {}
for r in records:
    by_name.setdefault(r['name'], []).append(r['index'])
print('\n-- checks --')
for name, want in probe.items():
    got = by_name.get(name, [])
    print('%-14s want %d  got %s  %s' % (name, want, got,
                                         'OK' if want in got else 'MISMATCH'))

with open(os.path.join(OUT, 'weapon_index_table.csv'), 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['index', 'name', 'dir_index', 'asset_size'])
    for r in records:
        w.writerow([r['index'], r['name'], r['dir_index'], r['size']])

with open(os.path.join(OUT, 'weapon_index_table.json'), 'w', encoding='utf-8') as fh:
    json.dump({'source_zone': ZONE,
               'order': 'XAsset directory order of type-28 (weapon) assets',
               'implicit': {'0': 'none', '1': 'defaultweapon_mp'},
               'records': records}, fh, ensure_ascii=False, indent=1)

print('\nwrote weapon_index_table.csv / .json  (%d entries)' % len(records))
