# -*- coding: utf-8 -*-
"""Recover the exact engine-index formula.

Observed:
  pool[0] = aa12_mp            (zone weapon-name pool, alphabetical, 1134 names)
  pool index of m4a1tech_mp = 583 -> engine 585
  pool index of vector_mp   = 1110 -> engine 1112
  pool index of m9_mp       = 644 -> engine 646

All three give engine = pool_index + 2.  The implicit definitions none (0) and
defaultweapon_mp (1) precede the pool, so pool[0] = engine 2.
"""
import csv, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
pool = [l.strip() for l in open(BASE + r'\zone_name_pool.txt', encoding='utf-8') if l.strip()]
idx = {}
for i, n in enumerate(pool):
    idx.setdefault(n, i)

OFFSET = 2
ANCH = {'m4a1tech_mp': 585, 'vector_mp': 1112, 'm9_mp': 646}
print('checks with engine = pool_index + %d' % OFFSET)
ok = True
for n, want in ANCH.items():
    p = idx[n]
    ok &= (p + OFFSET) == want
    print('  %-14s pool=%-5d engine=%-5d want=%-5d %s'
          % (n, p, p + OFFSET, want, 'OK' if p + OFFSET == want else 'BAD'))
print('RESULT:', 'PASS' if ok else 'FAIL')
assert ok

stats = {}
for w in csv.DictReader(open(BASE + r'\codol_weapon_table_3_19.csv', encoding='utf-8-sig')):
    stats[w['name']] = w

out = BASE + r'\codol_weapon_index_3_19.csv'
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    wr = csv.writer(fh)
    wr.writerow(['engine_index', 'name', 'clip_size', 'fire_time_ms', 'reload_ms',
                 'damage', 'player_damage', 'min_damage', 'max_damage_range',
                 'min_damage_range', 'base_name', 'ui_slots', 'verified'])
    wr.writerow([0, 'none', '', '', '', '', '', '', '', '', '', '', 'implicit'])
    wr.writerow([1, 'defaultweapon_mp', '', '', '', '', '', '', '', '', '', '', 'implicit'])
    for i, n in enumerate(pool):
        s = stats.get(n, {})
        wr.writerow([i + OFFSET, n, s.get('clip_size', ''), s.get('fire_time_ms', ''),
                     s.get('reload_ms', ''), s.get('damage', ''),
                     s.get('player_damage', ''), s.get('min_damage', ''),
                     s.get('max_damage_range', ''), s.get('min_damage_range', ''),
                     s.get('base_name', ''), s.get('ui_slots', ''),
                     'anchor-verified' if n in ANCH else ''])
print('\nwrote', out, 'rows', len(pool) + 2)
print('engine range: 0..%d' % (len(pool) + 1))
