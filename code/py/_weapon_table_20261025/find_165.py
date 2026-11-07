# -*- coding: utf-8 -*-
"""Find which table/column places m4a1tech_mp at 165 and fa1911ncm_mp at 77."""
import csv, glob, os, json, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
A, B = 'm4a1tech_mp', 'fa1911ncm_mp'
WA, WB = 165, 77

for zone_dir in ('st', 'st_common', 'st_firingrange'):
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
            vals = [r[c] for r in rows if len(r) > c]
            # first appearance index
            idx = {}
            for i, v in enumerate(vals):
                idx.setdefault(v, i)
            # last occurrence too
            last = {v: i for i, v in enumerate(vals)}
            for label, m in (('first', idx), ('last', last)):
                if A in m and B in m:
                    da, db = m[A] - WA, m[B] - WB
                    flag = ' <== MATCH' if (da == 0 and db == 0) else ''
                    if abs(da) < 60 and abs(db) < 60:
                        print('%-42s col=%d %-5s %s=%d(want %d) %s=%d(want %d)%s'
                              % (os.path.basename(p), c, label, A, m[A], WA,
                                 B, m[B], WB, flag))
print('done')
