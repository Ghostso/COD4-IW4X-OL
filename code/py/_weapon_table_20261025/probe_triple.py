# -*- coding: utf-8 -*-
"""Strongest available constraint: our own run's three anchors must be
CONSECUTIVE in any column that really is the engine weapon index.

    m4a1tech_mp = 1156, vector_mp = 1157, m9gold_mp = 1158

(after subtracting a constant offset, since the offset shifts per match).
"""
import csv, glob, os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
DIRS = [os.path.join(BASE, s) for s in ('st', 'st_common', 'st_market', 'st_firingrange')]
TRIPLE = ['m4a1tech_mp', 'vector_mp', 'm9gold_mp']


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
        nc, best = None, 0
        for c in range(cols):
            vals = [r[c] for r in rows if len(r) > c]
            n = sum(1 for v in vals if is_weapon(norm(v)))
            if n > best:
                best, nc = n, c
        if nc is None or best < 20:
            continue
        by = {}
        for r in rows:
            if len(r) > nc:
                by.setdefault(norm(r[nc]), r)
        if not all(t in by for t in TRIPLE):
            continue
        for c in range(cols):
            if c == nc:
                continue
            ok = True
            seq = []
            for t in TRIPLE:
                r = by[t]
                if len(r) <= c or not r[c].isdigit():
                    ok = False
                    break
                seq.append(int(r[c]))
            if not ok:
                continue
            if seq[1] == seq[0] + 1 and seq[2] == seq[1] + 1:
                print('*** CONSECUTIVE  %-40s col=%d  %s = %s'
                      % (os.path.basename(p), c, TRIPLE, seq))

print('scan done')
