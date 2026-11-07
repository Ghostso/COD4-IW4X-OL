# -*- coding: utf-8 -*-
"""Emit the final sellable catalogue: every trio item with no shop SKU priced
at 2400 CP permanent (user-specified)."""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'

PRICE_CP = 2400
CURRENCY_CP = 1
CATEGORY_COSMETIC = 3

census = list(csv.DictReader(open(os.path.join(BASE, 'codol_callsign_catalog_final.csv'),
                                  encoding='utf-8-sig')))
existing = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
next_id = max(int(e['Id']) for e in existing) + 1

rows = []
skipped_owned = 0
for r in census:
    if not r['itemId']:
        continue
    if r['商城SKU数'] and int(r['商城SKU数']) > 0:
        continue                       # already in the shop catalogue
    iid = int(r['itemId'])
    rows.append({
        'Id': next_id,
        'Item': iid,
        'Currency': CURRENCY_CP,
        'Price': PRICE_CP,
        'Category': CATEGORY_COSMETIC,
        'Stackable': False,
        'Grant': 1,
        'SelectedDays': 0,             # 0 = permanent
        '_类别': r['类别'],
        '_名称': r['ID'],
        '_中文名': r['中文名'],
    })
    next_id += 1

print('新增可售条目:', len(rows))
print('类别分布:', dict(collections.Counter(r['_类别'] for r in rows)))
print('统一价格: %d CP 永久' % PRICE_CP)
print('ID 区间: %d .. %d' % (rows[0]['Id'], rows[-1]['Id']))

out = os.path.join(BASE, 'marketplace_catalog_trio_2400cp.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['Id', 'Item', 'Currency', 'Price', 'Category',
                                       'Stackable', 'Grant', 'SelectedDays',
                                       '_类别', '_名称', '_中文名'])
    w.writeheader()
    w.writerows(rows)

# server-ready payload: the exact list the server appends to its catalogue
outj = os.path.join(BASE, 'marketplace_catalog_trio_2400cp.json')
with open(outj, 'w', encoding='utf-8') as fh:
    json.dump([{k: v for k, v in r.items() if not k.startswith('_')} for r in rows],
              fh, ensure_ascii=False, indent=1)

print('\nwrote', out)
print('wrote', outj)
print('\n=== 样例 ===')
for r in rows[:10]:
    print('  Id=%-6d Item=%-6d CP %d  %-26s %s'
          % (r['Id'], r['Item'], r['Price'], r['_名称'], r['_中文名'][:18]))
