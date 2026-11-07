# -*- coding: utf-8 -*-
"""Break the non-shop trio items down by naming pattern, to identify the
acquisition channel buried in the ID."""
import csv, os, io, sys, collections, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
rows = list(csv.DictReader(open(os.path.join(BASE, 'codol_callsign_full_census.csv'),
                                encoding='utf-8-sig')))

non = [r for r in rows if r['获取途径'] != '商城购买']
print('非商城条目:', len(non))
print()

# token frequency in the ID after the prefix
tok = collections.Counter()
for r in non:
    parts = re.split(r'[_]', r['ID'])
    for p in parts[1:]:
        tok[p] += 1
print('ID 里出现最多的片段（前 40）:')
for t, n in tok.most_common(40):
    print('  %-22s %d' % (t, n))

print()
print('=== 每类各举 12 个非商城条目 ===')
for lab in ('名片背景', '徽章', '称号'):
    print('\n---', lab, '---')
    n = 0
    for r in non:
        if r['类别'] != lab:
            continue
        print('  %-28s %-22s %s' % (r['ID'], r['中文名'][:22], r['itemId']))
        n += 1
        if n >= 12:
            break
