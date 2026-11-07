# -*- coding: utf-8 -*-
"""Test more registration-order hypotheses for the engine weapon index.

Anchor (this build): wire 1156 = m4a1tech_mp, 1157 = vector_mp, 1158 = m9gold_mp
(their clip/fire pairs 30/71, 36/59, 15/90 match the 3.19 zone WeaponDefs).
"""
import struct, re, csv, io, sys, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\common_mp.zone'
ST = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\st'
KEY = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_MP_NAME')
NAME = re.compile(rb'SF_WEAPON_([A-Z0-9_]+)_NAME')

d = open(ZONE, 'rb').read()
assets = []
for i in range(8557):
    typ, off, ptr, size = struct.unpack_from('<4I', d, 0xFC24 + i * 16)
    if typ != 28:
        continue
    b = d[0x28 + off: 0x28 + off + size]
    m = KEY.search(b)
    nm = m.group(1).decode().lower() + '_mp' if m else (
        NAME.search(b).group(1).decode().lower() if NAME.search(b) else '')
    assets.append({'dir': i, 'off': off, 'size': size, 'name': nm})

variant = set()
for r in csv.reader(open(ST + r'\mp_alt_weapon_lookup_table.csv', encoding='utf-8')):
    if r:
        variant.add(r[0])

ANCH = {'m4a1tech_mp': 1156, 'vector_mp': 1157, 'm9gold_mp': 1158}


def report(label, order):
    idx = {}
    for k, v in enumerate(order):
        idx.setdefault(v, k)
    got = {n: idx.get(n) for n in ANCH}
    diffs = {n: (got[n] - ANCH[n]) if got[n] is not None else None for n in ANCH}
    ok = all(v == 0 for v in diffs.values() if v is not None)
    print('%-38s n=%-5d %s%s' % (label, len(order), got, '  <== MATCH' if ok else ''))
    if not ok:
        print('%-38s deltas %s' % ('', diffs))


named = [a['name'] for a in assets if a['name']]
report('dir order, named only', named)
report('dir order, all (unnamed skipped)',
       [a['name'] if a['name'] else '?%d' % a['dir'] for a in assets])
report('offset order, named only',
       [a['name'] for a in sorted(assets, key=lambda a: a['off']) if a['name']])
report('offset order, all',
       [a['name'] if a['name'] else '?%d' % a['dir'] for a in sorted(assets, key=lambda a: a['off'])])
report('dir order, named, non-variant',
       [a['name'] for a in assets if a['name'] and a['name'] not in variant])
report('size order, named only',
       [a['name'] for a in sorted(assets, key=lambda a: a['size']) if a['name']])
report('reverse dir order, named only', list(reversed(named)))
