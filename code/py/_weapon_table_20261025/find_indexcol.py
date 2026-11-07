# -*- coding: utf-8 -*-
"""Find any dumped table/column where the value equals the row index (an
explicit index column), and report which one is weapon-keyed."""
import csv, glob, os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
DIRS = [os.path.join(BASE, s) for s in ('st', 'st_common', 'st_market', 'st_firingrange')]


def is_weapon(v):
    return v.endswith('_mp') or v.endswith('_so') or v.endswith('_zm')


def norm(v):
    if v.startswith('SF_WEAPON_') and v.endswith('_MP_NAME'):
        return v[len('SF_WEAPON_'):-len('_MP_NAME')].lower() + '_mp'
    return v


for d in DIRS:
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        try:
            rows = list(csv.reader(open(p, encoding='utf-8')))
        except Exception:
            continue
        if len(rows) < 20:
            continue
        cols = max(len(r) for r in rows)
        for c in range(cols):
            vals = [r[c] if len(r) > c else '' for r in rows]
            if not all(v.isdigit() for v in vals):
                continue
            nums = [int(v) for v in vals]
            hit = ''
            if nums == list(range(len(nums))):
                hit = 'ROWINDEX'
            elif nums == list(range(1, len(nums) + 1)):
                hit = 'ROWINDEX+1'
            if hit:
                wpn = 0
                for r in rows:
                    cells = [norm(x) for x in r[:2]]
                    if any(is_weapon(x) for x in cells):
                        wpn += 1
                print('%-11s %-42s col=%2d rows=%4d weapon-rows=%d'
                      % (hit, os.path.basename(p), c, len(nums), wpn))
print('done')
