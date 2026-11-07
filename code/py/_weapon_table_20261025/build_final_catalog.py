# -*- coding: utf-8 -*-
"""Final catalogue: Category corrected to 1 (the value real playercard shop
items use), and every entry tagged with whether its itemId is a known
marketplace id or an inventory-only id."""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'

PRICE_CP = 2400
CURRENCY_CP = 1
CATEGORY_ACCESSORY = 1        # measured: real playercard shop items use 1

cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-merged.json'), encoding='utf-8'))
cat_items = {int(e['Item']) for e in cat}
inv = json.load(open(os.path.join(KIT, 'marketplace-inventory.json'), encoding='utf-8'))['Items']
inv_items = {int(k) for k in inv if str(k).isdigit()}

census = list(csv.DictReader(open(os.path.join(BASE, 'codol_callsign_catalog_final.csv'),
                                  encoding='utf-8-sig')))
next_id = max(int(e['Id']) for e in cat) + 1

rows = []
for r in census:
    if not r['itemId']:
        continue
    if r['商城SKU数'] and int(r['商城SKU数']) > 0:
        continue
    iid = int(r['itemId'])
    known = 'marketplace-id' if iid in cat_items else (
        'inventory-only-id' if iid in inv_items else 'unknown-id')
    rows.append({
        'Id': next_id, 'Item': iid, 'Currency': CURRENCY_CP, 'Price': PRICE_CP,
        'Category': CATEGORY_ACCESSORY, 'Stackable': False, 'Grant': 1,
        'SelectedDays': 0,
        '_类别': r['类别'], '_名称': r['ID'], '_中文名': r['中文名'],
        '_ID性质': known,
    })
    next_id += 1

print('条目数:', len(rows))
print('Category 统一为:', CATEGORY_ACCESSORY)
print('价格统一为: %d CP 永久' % PRICE_CP)
print()
print('ID 性质分布:', dict(collections.Counter(r['_ID性质'] for r in rows)))
print('类别分布:', dict(collections.Counter(r['_类别'] for r in rows)))

out = os.path.join(BASE, 'marketplace_catalog_trio_final.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['Id', 'Item', 'Currency', 'Price', 'Category',
                                       'Stackable', 'Grant', 'SelectedDays',
                                       '_类别', '_名称', '_中文名', '_ID性质'])
    w.writeheader()
    w.writerows(rows)

outj = os.path.join(BASE, 'marketplace_catalog_trio_final.json')
with open(outj, 'w', encoding='utf-8') as fh:
    json.dump([{k: v for k, v in r.items() if not k.startswith('_')} for r in rows],
              fh, ensure_ascii=False, indent=1)
print('\nwrote', out)
print('wrote', outj)
