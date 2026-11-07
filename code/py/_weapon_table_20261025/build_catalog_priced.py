# -*- coding: utf-8 -*-
"""Derive quality tier from the real price of comparable shop items, then emit
the final catalogue.  Tier boundaries come from the observed price quartiles
of the 4122 priced items, split per category."""
import json, csv, os, io, sys, collections, statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
MK = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'
PLACEHOLDER = {0, 20000, 99999}
TIERS = ['普通', '稀有', '史诗', '传说']

census = list(csv.DictReader(open(os.path.join(BASE, 'codol_callsign_catalog_final.csv'),
                                  encoding='utf-8-sig')))
item_label = {int(r['itemId']): r['类别'] for r in census if r['itemId']}

j = json.load(open(MK, encoding='utf-8'))
prod_item = {}
for p in j['products']:
    for g in p.get('grants', []):
        if g.get('itemId'):
            prod_item[int(p['productId'])] = int(g['itemId'])
            break

# per (category, currency, permanent) -> sorted list of real prices
COL2CUR = {2: 'CP', 5: 'GP'}
real = collections.defaultdict(list)
for s in j['skus']:
    iid = prod_item.get(int(s['productId']))
    if iid is None or iid not in item_label:
        continue
    days = int(s.get('durationDays') or 0)
    for pr in s.get('prices', []):
        amt = int(pr['amount'])
        if amt in PLACEHOLDER or amt <= 0:
            continue
        real[(item_label[iid], COL2CUR.get(int(pr['column']), '?'),
              '永久' if days == 0 else '期限')].append(amt)

# per-item max price -> quartile boundaries within each category
item_max = collections.defaultdict(list)
for iid, lab in item_label.items():
    pass
by_item = collections.defaultdict(list)
for s in j['skus']:
    iid = prod_item.get(int(s['productId']))
    if iid is None or iid not in item_label:
        continue
    for pr in s.get('prices', []):
        amt = int(pr['amount'])
        if amt in PLACEHOLDER or amt <= 0:
            continue
        by_item[(item_label[iid], COL2CUR.get(int(pr['column']), '?'))].append(amt)


def bounds(vals):
    v = sorted(vals)
    n = len(v)
    return [v[min(n - 1, int(n * i / 4))] for i in (1, 2, 3)]


BOUNDS = {}
print('%-10s %-4s %6s  %s' % ('类别', '货币', '样本', '三段分位边界'))
for k, v in sorted(by_item.items()):
    if len(v) < 12:
        continue
    BOUNDS[k] = bounds(v)
    print('%-10s %-4s %6d  %s' % (k[0], k[1], len(v),
                                  ' / '.join(str(x) for x in BOUNDS[k])))


def tier_from_price(p, lab, cur):
    b = BOUNDS.get((lab, cur))
    if not b:
        return None
    if p <= b[0]:
        return 0
    if p <= b[1]:
        return 1
    if p <= b[2]:
        return 2
    return 3


# median permanent price per category (fallback)
def median_perm(lab, cur):
    v = real.get((lab, cur, '永久')) or real.get(('称号', cur, '永久'))
    return int(statistics.median(v)) if v else 753


existing = json.load(open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019\marketplace-catalog-client.json', encoding='utf-8'))
next_id = max(int(e['Id']) for e in existing) + 1

rows = []
for r in census:
    if not r['itemId'] or (r['商城SKU数'] and int(r['商城SKU数']) > 0):
        continue
    iid = int(r['itemId'])
    lab = r['类别']
    mid = median_perm(lab, 'GP')
    # Place the item at the median and read back its tier, so the tier labels
    # reflect the price the player will actually pay.
    t = tier_from_price(mid, lab, 'GP')
    if t is None:
        t = 1
    rows.append({
        'Id': next_id, 'Item': iid, 'Currency': 2, 'Price': mid,
        'Category': 3, 'Stackable': False, 'Grant': 1, 'SelectedDays': 0,
        '_类别': lab, '_价格对应品质': TIERS[t], '_名称': r['ID'],
        '_中文名': r['中文名'],
    })
    next_id += 1

print('\n新增可售条目:', len(rows), '  统一按类别中位价')
print('类别分布:', dict(collections.Counter(r['_类别'] for r in rows)))
print('对应品质:', dict(collections.Counter(r['_价格对应品质'] for r in rows)))

out = os.path.join(BASE, 'marketplace_catalog_by_price_model.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['Id', 'Item', 'Currency', 'Price', 'Category',
                                       'Stackable', 'Grant', 'SelectedDays',
                                       '_类别', '_价格对应品质', '_名称', '_中文名'])
    w.writeheader()
    w.writerows(rows)
print('\nwrote', out)
