# -*- coding: utf-8 -*-
"""Check whether the row order of mp/coWeapItemsWEA.csv is the engine weapon
index order (wire id), and what the numeric columns mean."""
import csv, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\st_market\mp_coweapitemswea.csv'
rows = list(csv.reader(open(P, encoding='utf-8')))
print('rows', len(rows), 'cols', len(rows[0]))

names = [r[1] for r in rows]  # localize key, more reliable than col0
def key(i):
    k = names[i]
    if k.startswith('SF_WEAPON_') and k.endswith('_MP_NAME'):
        return k[len('SF_WEAPON_'):-len('_MP_NAME')].lower() + '_mp'
    return k

for probe in ('m4a1tech_mp', 'vector_mp', 'm9gold_mp', 'm4_mp', 'ak47_mp', 'cheytac_mp'):
    want = 'SF_WEAPON_' + probe[:-3].upper() + '_MP_NAME'
    hits = [i for i, n in enumerate(names) if n == want]
    print('%-14s row=%s' % (probe, hits))

print()
print('-- numeric columns: distinct value counts --')
for c in range(len(rows[0])):
    vals = [r[c] for r in rows if len(r) > c]
    uniq = len(set(vals))
    numeric = sum(1 for v in vals if v.isdigit())
    if numeric > len(vals) * 0.8 and uniq > 50:
        print('  col %2d numeric=%.0f%% uniq=%d sample=%s'
              % (c, 100.0 * numeric / len(vals), uniq, vals[:8]))
