# -*- coding: utf-8 -*-
"""Scan every dumped stringtable for a (weapon-name column, unique-integer
column) pair -- i.e. a table that assigns a number to each weapon name."""
import csv, glob, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

DIRS = [r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025' + s
        for s in ('\\st', '\\st_market', '\\st_common', '\\st_firingrange')]

NAME_COL = 1  # 0 = weapon name, 1 = SF_WEAPON_*_MP_NAME


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
        if len(rows) < 30:
            continue
        cols = max(len(r) for r in rows)
        # find the weapon-name column
        name_col, best = None, 0
        for c in range(cols):
            vals = [r[c] for r in rows if len(r) > c]
            n = sum(1 for v in vals if is_weapon(norm(v)))
            if n > best:
                best, name_col = n, c
        if name_col is None or best < 30:
            continue
        for c in range(cols):
            if c == name_col:
                continue
            vals = [r[c] for r in rows if len(r) > c]
            if not vals:
                continue
            ints = [v for v in vals if v.isdigit()]
            if len(ints) < len(vals) * 0.8:
                continue
            nums = [int(v) for v in ints]
            if not nums or max(nums) > 5000:
                continue
            # unique per weapon name?
            pairs = [(norm(r[name_col]), int(r[c])) for r in rows
                     if len(r) > c and r[c].isdigit()]
            if len(set(pairs)) != len(pairs):
                continue
            per_name = collections.defaultdict(set)
            for nm, v in pairs:
                per_name[nm].add(v)
            if any(len(s) > 1 for s in per_name.values()):
                continue
            print('%-46s name_col=%d num_col=%d rows=%d range=%d..%d'
                  % (os.path.basename(p), name_col, c, len(pairs),
                     min(nums), max(nums)))
