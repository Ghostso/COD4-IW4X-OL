# -*- coding: utf-8 -*-
"""Build a 4-tier price model from the real shop prices, then price every
trio item that has no SKU.

Tier order (user-confirmed): 普通 < 稀有 < 史诗 < 传说
Prices are quantile-cut per (category, currency, permanent) so that the same
proportions of the real catalogue land in each tier.
"""
import json, csv, os, io, sys, collections, statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
MK = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'
PLACEHOLDER = {0, 99999, 20000}

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

# collect real prices: (label, currency, permanent?) -> [amounts]
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

TIERS = ['普通', '稀有', '史诗', '传说']
model = {}
print('%-10s %-4s %-6s %6s  %s' % ('类别', '货币', '类型', '样本',
                                   '  '.join('%-7s' % t for t in TIERS)))
for key, vals in sorted(real.items()):
    if len(vals) < 8:
        continue
    vals = sorted(vals)
    n = len(vals)
    # 4 ascending quantile buckets -> one representative price each (median)
    cuts = [vals[int(n * i / 4)] for i in range(4)]
    reps = []
    for i in range(4):
        lo = int(n * i / 4)
        hi = int(n * (i + 1) / 4)
        seg = vals[lo:hi] or [cuts[i]]
        reps.append(int(statistics.median(seg)))
    model[key] = reps
    print('%-10s %-4s %-6s %6d  %s' % (key[0], key[1], key[2], n,
                                       '  '.join('%-7d' % r for r in reps)))

out = os.path.join(BASE, 'price_model_4tier.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['类别', '货币', '类型', '样本数'] + TIERS)
    for key, reps in sorted(model.items()):
        n = len(real[key])
        w.writerow([key[0], key[1], key[2], n] + reps)
print('\nwrote', out)
