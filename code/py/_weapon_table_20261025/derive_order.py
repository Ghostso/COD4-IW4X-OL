# -*- coding: utf-8 -*-
"""Derive the engine weapon index order from coweaponattachmenttable.csv row order.

Hypothesis under test: the client registers MP weapons in first-appearance
order of column 0 in mp/coweaponattachmenttable.csv, preceded by the two
implicit definitions (none, defaultweapon_mp).
"""
import csv, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

SRC = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\coweaponattachmenttable.csv'

order = []
seen = set()
with open(SRC, encoding='utf-8') as fh:
    for row in csv.reader(fh):
        if not row:
            continue
        w = row[0]
        if w in seen:
            continue
        seen.add(w)
        order.append(w)

print('unique weapon names in row order:', len(order))
for i, w in enumerate(order[:30]):
    print('  %4d %s' % (i, w))

# Where do the known runtime ids land under this hypothesis?
base = 2  # none=0, defaultweapon_mp=1
idx = {w: i + base for i, w in enumerate(order)}
for probe in ('m4a1tech_mp', 'ak47_mp', 'cheytac_mp', 'wa2000_mp', 'mp5k_mp',
              'ak104_mp', 'ump45_mp', 'r870_mp'):
    print('%-16s -> %s' % (probe, idx.get(probe)))
