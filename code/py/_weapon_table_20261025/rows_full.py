# -*- coding: utf-8 -*-
"""Dump full rows of coWeapItemsWEA for known weapons, with column indices."""
import csv, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\st_market\mp_coweapitemswea.csv'
rows = list(csv.reader(open(P, encoding='utf-8')))


def key(r):
    k = r[1]
    if k.startswith('SF_WEAPON_') and k.endswith('_MP_NAME'):
        return k[len('SF_WEAPON_'):-len('_MP_NAME')].lower() + '_mp'
    return k


for probe in ('m4a1tech_mp', 'm4_mp', 'ak47_mp', 'cheytac_mp', 'vector_mp',
              'm9gold_mp', 'fa1911ncm_mp'):
    for r in rows:
        if key(r) == probe:
            print('%-14s row=%d' % (probe, rows.index(r)))
            for i, v in enumerate(r):
                if v and v != '<unresolved 00000000>':
                    print('    [%2d] %s' % (i, v))
            print()
            break

print('-- col55 distribution --')
vals = [(key(r), r[55]) for r in rows if len(r) > 55 and r[55].isdigit()]
nums = sorted(int(v) for _, v in vals)
print('count', len(nums), 'min', nums[0], 'max', nums[-1])
print('first 20 by value:', sorted(vals, key=lambda x: int(x[1]))[:12])
for probe in ('m4a1tech_mp', 'm4_mp', 'ak47_mp', 'cheytac_mp'):
    print(probe, [v for k, v in vals if k == probe])
