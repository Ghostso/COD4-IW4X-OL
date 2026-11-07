# -*- coding: utf-8 -*-
"""Does MarketplaceSkus.json carry the playercard SKU rows we need?"""
import json, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'
j = json.load(open(P, encoding='utf-8'))

print('top keys:', list(j.keys()))
print('source.tables:', j['source'].get('tables'))
print('skuCount', j['source'].get('skuCount'), 'productCount', j['source'].get('productCount'))

skus = j.get('skus') or []
print('\nskus entries:', len(skus))
if skus:
    print('sample[0]:', json.dumps(skus[0], ensure_ascii=False))
    print('keys of sku:', list(skus[0].keys()))

# how many skus reference an Item in the playercard band?
band = collections.Counter()
for s in skus:
    it = s.get('itemId') or s.get('Item') or s.get('item')
    if it is None:
        continue
    band[int(it) // 10000 * 10000] += 1
print('\nskus by itemId band:')
for b in sorted(band):
    print('  %6d..  %6d  %d' % (b, b + 9999, band[b]))
