# -*- coding: utf-8 -*-
"""Search every dumped stringtable column for a dense list of weapon names."""
import csv, glob, os, re, json, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
BASE = os.path.join(ROOT, '_weapon_table_20261025')
DEFS = os.path.join(ROOT, 'CODOL_SERVER_319_20261021', 'fixtures',
                    'common_mp_weapondefs_20261023.json')

known = set(w['name'] for w in json.load(open(DEFS, encoding='utf-8'))['weapons'])
print('known weapon names from zone WeaponDefs:', len(known))

for zone_dir in ('st', 'st_firingrange'):
    d = os.path.join(BASE, zone_dir)
    if not os.path.isdir(d):
        continue
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        try:
            rows = list(csv.reader(open(p, encoding='utf-8')))
        except Exception:
            continue
        if not rows:
            continue
        cols = max(len(r) for r in rows)
        for c in range(cols):
            vals = [r[c] for r in rows if len(r) > c and r[c]]
            if not vals:
                continue
            hit = sum(1 for v in vals if v in known)
            if hit >= 40 and hit >= 0.5 * len(vals):
                print('%-46s col=%d rows=%d hits=%d' % (os.path.basename(p), c,
                                                        len(vals), hit))
