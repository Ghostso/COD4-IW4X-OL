# -*- coding: utf-8 -*-
"""Two probes:
1) Find any (table, column) where m4a1tech_mp and fa1911ncm_mp differ by 88
   (the two known native asset indices 165 and 77 from a real match).
2) Show the value format of mp/coweapitemswea.csv column 55.
"""
import csv, glob, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
DIRS = [os.path.join(BASE, s) for s in ('st', 'st_market', 'st_common', 'st_firingrange')]
A, B, DIFF = 'm4a1tech_mp', 'fa1911ncm_mp', 88


def is_weapon(v):
    return v.endswith('_mp') or v.endswith('_so') or v.endswith('_zm')


def norm(v):
    if v.startswith('SF_WEAPON_') and v.endswith('_MP_NAME'):
        return v[len('SF_WEAPON_'):-len('_MP_NAME')].lower() + '_mp'
    return v


print('=== probe 1: columns where A - B == 88 ===')
for d in DIRS:
    for p in sorted(glob.glob(os.path.join(d, '*.csv'))):
        try:
            rows = list(csv.reader(open(p, encoding='utf-8')))
        except Exception:
            continue
        if len(rows) < 20:
            continue
        cols = max(len(r) for r in rows)
        # locate name column
        nc, best = None, 0
        for c in range(cols):
            vals = [r[c] for r in rows if len(r) > c]
            n = sum(1 for v in vals if is_weapon(norm(v)))
            if n > best:
                best, nc = n, c
        if nc is None or best < 20:
            continue
        # index rows by weapon name
        by = {}
        for r in rows:
            if len(r) > nc:
                by.setdefault(norm(r[nc]), r)
        if A not in by or B not in by:
            continue
        ra, rb = by[A], by[B]
        for c in range(cols):
            if c == nc or len(ra) <= c or len(rb) <= c:
                continue
            va, vb = ra[c], rb[c]
            if va.isdigit() and vb.isdigit() and int(va) - int(vb) == DIFF:
                print('  %-40s col=%d  %s=%s  %s=%s'
                      % (os.path.basename(p), c, A, va, B, vb))

print()
print('=== probe 2: coweapitemswea col 55 format ===')
P = os.path.join(BASE, 'st_market', 'mp_coweapitemswea.csv')
rows = list(csv.reader(open(P, encoding='utf-8')))
vals = [r[55] if len(r) > 55 else '' for r in rows]
nonnum = [v for v in vals if v and not v.isdigit()]
print('  rows', len(rows), 'empty', sum(1 for v in vals if not v),
      'non-numeric', len(nonnum))
print('  non-numeric samples:', collections.Counter(nonnum).most_common(10))
nums = [int(v) for v in vals if v.isdigit()]
print('  numeric range', min(nums), '..', max(nums), 'count', len(nums),
      'distinct', len(set(nums)))
dups = collections.Counter(nums)
print('  duplicated values:', [(v, c) for v, c in dups.most_common(8) if c > 1])
