# -*- coding: utf-8 -*-
"""Inventory every dumped stringtable: rows, cols, and a sample of column 0."""
import csv, glob, os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
DIRS = ['st', 'st_market', 'st_common', 'st_gt', 'st_firingrange']

seen = {}
for sub in DIRS:
    for p in sorted(glob.glob(os.path.join(BASE, sub, '*.csv'))):
        name = os.path.basename(p)
        if 'coweapmodels' in name or 'cocharavailableitems' in name or 'cocharitems' in name:
            continue
        try:
            rows = list(csv.reader(open(p, encoding='utf-8')))
        except Exception:
            continue
        if not rows:
            continue
        cols = max(len(r) for r in rows)
        key = name
        if key in seen:
            seen[key][1] += 1
            continue
        sample = [r[0] for r in rows[:2] if r]
        seen[key] = [sub, 1, len(rows), cols, sample]

items = sorted(seen.items(), key=lambda kv: -kv[1][2])
print('%-52s %-14s %6s %4s  %s' % ('table', 'zone', 'rows', 'cols', 'first cells'))
for name, (sub, _, n, cols, sample) in items:
    print('%-52s %-14s %6d %4d  %s' % (name[:52], sub, n, cols, str(sample)[:60]))
