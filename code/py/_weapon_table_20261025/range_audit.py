# -*- coding: utf-8 -*-
"""Investigate the two itemId ranges for playercards.

Range A (11000-11199): present in the shop catalogue, Category 1.
Range B (30000-30999): the ids our census uses, absent from the catalogue.

Question: are range-B ids real marketplace items, or account-inventory ids
that the marketplace never sells?
"""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'

cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-merged.json'), encoding='utf-8'))
cat_items = {int(e['Item']) for e in cat}
inv = json.load(open(os.path.join(KIT, 'marketplace-inventory.json'), encoding='utf-8'))['Items']
inv_items = {int(k) for k in inv if str(k).isdigit()}

MK = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'
j = json.load(open(MK, encoding='utf-8'))
nm = {}
for p in j['products']:
    for g in p.get('grants', []):
        if g.get('itemId') and g.get('name'):
            nm.setdefault(int(g['itemId']), g['name'])

BANDS = [('11000 段', 11000, 11200), ('30000 段', 30000, 31000), ('60000 段', 60000, 60100)]

print('%-12s %8s %10s %10s %10s' % ('ID 段', '有名', '在目录', '在库存', '两者都'))
for label, lo, hi in BANDS:
    ids = [i for i in nm if lo <= i < hi]
    in_cat = sum(1 for i in ids if i in cat_items)
    in_inv = sum(1 for i in ids if i in inv_items)
    both = sum(1 for i in ids if i in cat_items and i in inv_items)
    print('%-12s %8d %10d %10d %10d' % (label, len(ids), in_cat, in_inv, both))

print()
print('=== 11000 段样例（目录里能卖的）===')
n = 0
for i in sorted(nm):
    if 11000 <= i < 11200 and i in cat_items:
        rows = [e for e in cat if int(e['Item']) == i]
        print('  Item=%-6d %-22s Cat=%s  %s'
              % (i, nm[i], {int(e['Category']) for e in rows},
                 ' '.join('%s%d/%dd' % ('CP' if e['Currency'] == 1 else 'GP',
                                        e['Price'], e['SelectedDays']) for e in rows[:4])))
        n += 1
        if n >= 6:
            break

print()
print('=== 30000 段样例（我们的清单用的）===')
n = 0
for i in sorted(nm):
    if 30000 <= i < 31000:
        print('  Item=%-6d %-24s 在目录=%s 在库存=%s'
              % (i, nm[i], i in cat_items, i in inv_items))
        n += 1
        if n >= 10:
            break
