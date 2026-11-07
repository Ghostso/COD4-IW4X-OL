# -*- coding: utf-8 -*-
"""Derive a price-by-tier table from the 477 real shop items, grouped by
category, so the unpriced items can borrow a defensible price."""
import json, csv, os, io, sys, collections, statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'

census = list(csv.DictReader(open(os.path.join(BASE, 'codol_callsign_catalog_final.csv'),
                                  encoding='utf-8-sig')))

MK = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'
j = json.load(open(MK, encoding='utf-8'))
prod_item = {}
for p in j['products']:
    for g in p.get('grants', []):
        if g.get('itemId'):
            prod_item[int(p['productId'])] = int(g['itemId'])
            break

# itemId -> label
item_label = {}
for r in census:
    if r['itemId']:
        item_label[int(r['itemId'])] = r['类别']

skus = collections.defaultdict(list)   # itemId -> [(col, amount, days)]
for s in j['skus']:
    iid = prod_item.get(int(s['productId']))
    if iid is None or iid not in item_label:
        continue
    for pr in s.get('prices', []):
        skus[iid].append((int(pr['column']), int(pr['amount']),
                          int(s.get('durationDays') or 0)))

print('有名片的商城 item 数:', len(skus))

# price by (label, currency-column, duration)
PLACEHOLDER = {99999, 20000}      # 20000/99999 are "not for sale" sentinels
agg = collections.defaultdict(list)
for iid, lst in skus.items():
    lab = item_label[iid]
    for col, amt, days in lst:
        if amt <= 0 or amt in PLACEHOLDER:
            continue
        agg[(lab, col, days)].append(amt)

COL2CUR = {2: 'CP', 5: 'GP'}
print('\n%-10s %-4s %-6s %6s %8s %8s %8s' %
      ('类别', '货币', '期限', '样本', '中位', '最低', '最高'))
rows = []
for (lab, col, days), vals in sorted(agg.items()):
    if len(vals) < 3:
        continue
    med = statistics.median(vals)
    rows.append((lab, COL2CUR.get(col, str(col)), days, len(vals),
                 int(med), min(vals), max(vals)))
    print('%-10s %-4s %-6d %6d %8d %8d %8d'
          % (lab, COL2CUR.get(col, str(col)), days, len(vals), med, min(vals), max(vals)))

out = os.path.join(BASE, 'price_reference_by_tier.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['类别', '货币', '期限天', '样本数', '中位价', '最低价', '最高价'])
    w.writerows(rows)
print('\nwrote', out)
