# -*- coding: utf-8 -*-
"""Split the trio into owned / not-owned and check which side lacks catalog SKUs."""
import json, os, csv, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'

inv = json.load(open(os.path.join(KIT, 'marketplace-inventory.json'), encoding='utf-8'))['Items']
cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
sku_by_item = collections.Counter(int(e['Item']) for e in cat)

rows = list(csv.DictReader(open(os.path.join(BASE, 'playercard_trio_audit.csv'), encoding='utf-8-sig')))

grp = collections.defaultdict(lambda: {'owned': 0, 'unowned': 0, 'owned_sku': 0, 'unowned_sku': 0})
for r in rows:
    lab = r['类别']
    iid = int(r['itemId'])
    has_sku = sku_by_item.get(iid, 0) > 0
    owned = str(iid) in inv
    if owned:
        grp[lab]['owned'] += 1
        if has_sku:
            grp[lab]['owned_sku'] += 1
    else:
        grp[lab]['unowned'] += 1
        if has_sku:
            grp[lab]['unowned_sku'] += 1

print('%-10s %8s %8s %10s %10s' % ('类别', '已拥有', '未拥有', '已拥有有SKU', '未拥有有SKU'))
tot = collections.Counter()
for k in sorted(grp):
    g = grp[k]
    print('%-10s %8d %8d %10d %10d' % (k, g['owned'], g['unowned'],
                                       g['owned_sku'], g['unowned_sku']))
    for f in g:
        tot[f] += g[f]
print('%-10s %8d %8d %10d %10d' % ('合计', tot['owned'], tot['unowned'],
                                   tot['owned_sku'], tot['unowned_sku']))

# export the unowned ones (the ones the user actually tries to buy)
un = [r for r in rows if str(r['itemId']) not in inv]
out = os.path.join(BASE, 'playercard_trio_unowned.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(un)
print('\n未拥有条目:', len(un), '-> ', out)
print('\n样例:')
for r in un[:12]:
    print('  %-6s %-6s %-26s %-16s SKU=%s' % (r['类别'], r['itemId'], r['内部名'],
                                              r['中文名'][:16], r['目录SKU数']))
