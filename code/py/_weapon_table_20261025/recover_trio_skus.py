# -*- coding: utf-8 -*-
"""Join MarketplaceSkus.json (skus -> products -> grants) to recover the real
SKU catalogue for the playercard / emblem / title trio."""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
MK = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'

j = json.load(open(MK, encoding='utf-8'))
products = {int(p['productId']): p for p in j['products']}
skus = j['skus']

# productId -> itemId (+ name)
prod_item = {}
for pid, p in products.items():
    for g in p.get('grants', []):
        if g.get('itemId'):
            prod_item[pid] = (int(g['itemId']), g.get('name', ''))
            break

PREFIX = [('pcb_', '名片背景'), ('pci_', '徽章'), ('pct_', '称号'),
          ('pcf_', '边框'), ('pcn_', '名牌'), ('pcai_', '动态图标'),
          ('pcab_', '动态背景'), ('pcaf_', '动态边框')]


def label_of(name):
    for pre, lab in PREFIX:
        if name.startswith(pre):
            return lab
    return None


rows = []
for s in skus:
    pid = int(s['productId'])
    if pid not in prod_item:
        continue
    iid, nm = prod_item[pid]
    lab = label_of(nm)
    if not lab:
        continue
    for pr in s.get('prices', []):
        rows.append({
            '类别': lab,
            'sku': s['sku'],
            'productId': pid,
            'itemId': iid,
            '内部名': nm,
            '价格': pr.get('amount'),
            '货币列': pr.get('column'),
            '期限天': s.get('durationDays'),
            '开售': s.get('availableFrom'),
            '停售': s.get('availableUntil'),
        })

print('三件套 SKU 行数（按币种展开）:', len(rows))
by = collections.Counter(r['类别'] for r in rows)
for k, v in by.most_common():
    print('  %-8s %d' % (k, v))

out = os.path.join(BASE, 'playercard_trio_skus.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['类别', 'sku', 'productId', 'itemId', '内部名',
                                       '价格', '货币列', '期限天', '开售', '停售'])
    w.writeheader()
    w.writerows(rows)
print('\nwrote', out)

print('\n=== 样例 ===')
for r in rows[:10]:
    print('  %-6s sku=%-6d item=%-6d %-24s %s %d 天'
          % (r['类别'], r['sku'], r['itemId'], r['内部名'],
             r['价格'], r['期限天'] if r['期限天'] is not None else -1))
