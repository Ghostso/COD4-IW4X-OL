# -*- coding: utf-8 -*-
"""Join the marketplace SKU catalog with the item table (callsigns/badges/etc.)
to see how many catalog entries correspond to named in-game items."""
import json, csv, io, sys, collections, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\WEAPON_READ_20261022\kit'

cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
print('catalog entries', len(cat))

items = list(csv.DictReader(open(os.path.join(BASE, 'codol_items_3_19.csv'), encoding='utf-8-sig')))
print('item rows', len(items))

# Catalog.Item is the marketplace "item id" (10001-style), not our string IDs.
print('catalog Item id range', min(e['Item'] for e in cat), '..', max(e['Item'] for e in cat))

# marketplace skus json (ol-mod assets) maps itemId -> name
skus_path = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'
mk = json.load(open(skus_path, encoding='utf-8'))
prod = {}
for p in mk['products']:
    for g in p.get('grants', []):
        if g.get('itemId'):
            prod.setdefault(int(g['itemId']), g.get('name', ''))
print('marketplace products with itemId', len(prod))

named = sum(1 for e in cat if int(e['Item']) in prod)
print('catalog rows whose Item resolves to a name:', named, '/', len(cat))

# distribution by item id band
band = collections.Counter()
for e in cat:
    band[int(e['Item']) // 1000 * 1000] += 1
print('\ntop item-id bands:')
for b, n in band.most_common(12):
    print('  %6d.. %6d' % (b, n))

# sample of resolved names
res = [(e['Id'], e['Item'], prod[int(e['Item'])], e['Price'], e['Currency'])
       for e in cat if int(e['Item']) in prod]
print('\nsample resolved:', res[:10])
