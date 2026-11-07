# -*- coding: utf-8 -*-
"""Final trio catalogue: three honest acquisition buckets only."""
import csv, os, io, sys, collections, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
SRC = os.path.join(BASE, 'codol_callsign_full_census.csv')
OUT = os.path.join(BASE, 'codol_callsign_catalog_final.csv')

rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig')))

# Only two things are actually established: whether a shop SKU exists, and
# whether the ID names a concrete seasonal/event programme.
SEASON_RX = re.compile(r'(s\d+(bronze|silver|gold|platinum|diamond|glory|wargod)'
                       r'|wargod|bounty|zchamp|zarena|zhunt|zombie|prestige|pres\d'
                       r'|daily|weekly|challenge|champ|clan|wegame|tgp)', re.I)

for r in rows:
    if r['商城SKU数'] and int(r['商城SKU数']) > 0:
        r['获取途径'] = '商城购买'
    elif SEASON_RX.search(r['ID']):
        r['获取途径'] = '赛季/活动奖励'
    elif r['ID'].lower().endswith('_default'):
        r['获取途径'] = '默认赠送'
    else:
        r['获取途径'] = '奖励发放（途径未标明）'

agg = collections.defaultdict(lambda: collections.Counter())
total = collections.Counter()
for r in rows:
    agg[r['类别']][r['获取途径']] += 1
    total[r['获取途径']] += 1

LABELS = ['商城购买', '赛季/活动奖励', '默认赠送', '奖励发放（途径未标明）']
print('%-10s %s %s' % ('类别', ''.join('%14s' % l for l in LABELS), '   合计'))
for lab in ('名片背景', '徽章', '称号', '边框', '名牌'):
    c = agg[lab]
    print('%-10s %s %6d' % (lab, ''.join('%14d' % c[l] for l in LABELS), sum(c.values())))
print('%-10s %s %6d' % ('合计', ''.join('%14d' % total[l] for l in LABELS), sum(total.values())))

with open(OUT, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['类别', 'ID', '名称键', '中文名', 'itemId',
                                       '商城SKU数', '获取途径'])
    w.writeheader()
    w.writerows(rows)
print('\nwrote', OUT, len(rows), 'rows')
print('有中文名:', sum(1 for r in rows if r['中文名']), '/', len(rows))
