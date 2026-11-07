# -*- coding: utf-8 -*-
"""Second anchor set (from composite-gamestate-candidate.json):
    m4a1tech_mp  base weapon = 585
    vector_mp    base weapon = 1112
    m9_mp        base weapon = 646

585 and 646 sit inside the stock range; 1112 is above firstDynamicWeapon 1147?
No -- 1112 < 1147, so all three are stock indices. Test every ordering and
formula we have against these.
"""
import csv, struct, re, glob, os, io, sys, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
ANCH = {'m4a1tech_mp': 585, 'vector_mp': 1112, 'm9_mp': 646}
print('anchors', ANCH)

# --- candidate 1: coWeapItemsWEA col55 ---
rows = list(csv.reader(open(BASE + r'\st_market\mp_coweapitemswea.csv', encoding='utf-8')))


def key(r):
    k = r[1] if len(r) > 1 else ''
    if k.startswith('SF_WEAPON_') and k.endswith('_MP_NAME'):
        return k[len('SF_WEAPON_'):-len('_MP_NAME')].lower() + '_mp'
    return None


col55 = {}
for r in rows:
    k = key(r)
    if k and len(r) > 55 and r[55].isdigit():
        col55.setdefault(k, int(r[55]))
print('\ncoWeapItemsWEA col55:')
for n, w in ANCH.items():
    print('  %-14s col55=%-5s want %d' % (n, col55.get(n), w))

# --- candidate 2: zone order in common_mp, various filters ---
z = open(BASE + r'\common_mp.zone', 'rb').read()
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
items = []
for i in range(8557):
    t, off, ptr, sz = struct.unpack_from('<4I', z, 0xFC24 + i * 16)
    if t != 28:
        continue
    b = z[0x28 + off: 0x28 + off + sz]
    m = KEY.search(b)
    items.append({'dir': i, 'off': off, 'size': sz,
                  'name': m.group(1).decode().lower() + '_mp' if m else None})

variant = set()
for r in csv.reader(open(BASE + r'\st\mp_alt_weapon_lookup_table.csv', encoding='utf-8')):
    if r:
        variant.add(r[0])


def report(label, order):
    idx = {}
    for k, v in enumerate(order):
        if v:
            idx.setdefault(v, k)
    got = {n: idx.get(n) for n in ANCH}
    diffs = {n: (got[n] - ANCH[n]) if got[n] is not None else None for n in ANCH}
    match = all(v == 0 for v in diffs.values() if v is not None)
    print('%-40s %s%s' % (label, got, '   <== MATCH' if match else ''))


print('\nzone orderings (common_mp):')
report('all type28, dir order', [x['name'] for x in items])
report('named only, dir order', [x['name'] for x in items if x['name']])
report('named, non-variant, dir order',
       [x['name'] if x['name'] not in variant else None for x in items])
report('named only, offset order',
       [x['name'] for x in sorted(items, key=lambda x: x['off'])if x['name']])
