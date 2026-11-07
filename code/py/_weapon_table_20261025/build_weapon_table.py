# -*- coding: utf-8 -*-
"""Build the CODOL 3.19 weapon table: name, base name, stats, and every
index we can defensibly attach.

Inputs (all read-only, all re-derivable):
  common_mp.zone               type-28 (weapon) asset directory order
  common_mp_weapondefs.json    zone-verified stats per weapon name
  st/mp_alt_weapon_lookup_table.csv   variant -> base name
  st/mp_coweaponuislottable.csv       weapon -> attachment slots
"""
import struct, re, json, csv, os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
BASE = os.path.join(ROOT, '_weapon_table_20261025')
ZONE = os.path.join(BASE, 'common_mp.zone')
DEFS = os.path.join(ROOT, 'CODOL_SERVER_319_20261021', 'fixtures',
                    'common_mp_weapondefs_20261023.json')
ALT = os.path.join(BASE, 'st', 'mp_alt_weapon_lookup_table.csv')
SLOTS = os.path.join(BASE, 'st', 'mp_coweaponuislottable.csv')

DIR_OFF, DIR_COUNT, ASSET_BASE = 0xFC24, 8557, 0x28
KEY_RE = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
NAME_RE = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_NAME')

d = open(ZONE, 'rb').read()
zone_order = []
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
        nm = m2.group(1).decode('ascii').lower() if m2 else ''
    zone_order.append({'zone_pos': len(zone_order), 'name': nm,
                       'dir_index': i, 'asset_size': size})

stats = {}
for w in json.load(open(DEFS, encoding='utf-8'))['weapons']:
    stats[w['name']] = w

base_of = {}
for row in csv.reader(open(ALT, encoding='utf-8')):
    if len(row) >= 2:
        base_of[row[0]] = row[1]

slot_count = {}
for row in csv.reader(open(SLOTS, encoding='utf-8')):
    if row:
        slot_count[row[0]] = slot_count.get(row[0], 0) + 1

out = os.path.join(BASE, 'codol_weapon_table_3_19.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['zone_pos', 'name', 'base_name', 'ui_slots', 'clip_size',
                'fire_time_ms', 'reload_ms', 'damage', 'player_damage',
                'min_damage', 'max_damage_range', 'min_damage_range',
                'dir_index', 'asset_size', 'stats_verified'])
    for r in zone_order:
        s = stats.get(r['name'], {})
        w.writerow([r['zone_pos'], r['name'], base_of.get(r['name'], ''),
                    slot_count.get(r['name'], ''), s.get('clip_size', ''),
                    s.get('fire_time_ms', ''), s.get('reload_ms', ''),
                    s.get('damage', ''), s.get('player_damage', ''),
                    s.get('min_damage', ''), s.get('max_damage_range', ''),
                    s.get('min_damage_range', ''), r['dir_index'],
                    r['asset_size'], s.get('status', '')])

named = [r for r in zone_order if r['name']]
print('zone type-28 assets      :', len(zone_order))
print('with a resolved name     :', len(named))
print('with zone-verified stats :', sum(1 for r in zone_order if r['name'] in stats))
print('variants with a base name:', len(base_of))
print('wrote', out)
