# -*- coding: utf-8 -*-
"""Reverse the Category enum from the real catalogue: for every Category value,
list the item-name prefixes that appear under it, weighted by count."""
import json, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'

cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-merged.json'), encoding='utf-8'))
MK = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'
j = json.load(open(MK, encoding='utf-8'))
nm = {}
for p in j['products']:
    for g in p.get('grants', []):
        if g.get('itemId') and g.get('name'):
            nm.setdefault(int(g['itemId']), g['name'])

by = collections.defaultdict(collections.Counter)
unnamed = collections.Counter()
for e in cat:
    c = int(e['Category'])
    n = nm.get(int(e['Item']))
    if n:
        by[c][n.split('_')[0]] += 1
    else:
        unnamed[c] += 1

print('=== 每个 Category 下出现的道具名前缀 ===')
for c in sorted(by):
    tot = sum(by[c].values()) + unnamed[c]
    print('\nCategory %d  (共 %d 条, 有名 %d, 无名 %d)'
          % (c, tot, sum(by[c].values()), unnamed[c]))
    for pre, n in by[c].most_common(14):
        print('    %-16s %d' % (pre, n))
