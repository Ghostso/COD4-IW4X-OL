# -*- coding: utf-8 -*-
"""Full trio census: client stringtables (authoritative) vs marketplace SKUs,
and classify acquisition channel."""
import csv, json, os, io, sys, collections, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
ST = os.path.join(BASE, 'st')
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'

TABLES = [
    ('名片背景', 'mp_callsignbackground.csv'),
    ('徽章',     'mp_callsignicon.csv'),
    ('称号',     'mp_callsigntitle.csv'),
    ('边框',     'mp_callsignframe.csv'),
    ('名牌',     'mp_callsignnameplate.csv'),
]

zh = {r['key']: r['text_zh']
      for r in csv.DictReader(open(os.path.join(BASE, 'localize_zh.csv'), encoding='utf-8-sig'))}


def zh_of(key):
    if not key:
        return ''
    for k in (key, key.upper()):
        v = zh.get(k)
        if v and v.strip():
            return v
    return ''


# ---- marketplace: itemId -> (skus, prices, days) ----
MK = r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json'
j = json.load(open(MK, encoding='utf-8'))
prod_item = {}
for p in j['products']:
    for g in p.get('grants', []):
        if g.get('itemId'):
            prod_item[int(p['productId'])] = int(g['itemId'])
            break
shop_items = collections.defaultdict(list)
for s in j['skus']:
    iid = prod_item.get(int(s['productId']))
    if iid is not None:
        shop_items[iid].append(s)

# ---- id -> itemId bridge via MarketplaceSkus names ----
name_item = {}
for p in j['products']:
    for g in p.get('grants', []):
        if g.get('itemId') and g.get('name'):
            name_item.setdefault(g['name'], int(g['itemId']))

rows = []
for label, fn in TABLES:
    data = list(csv.reader(open(os.path.join(ST, fn), encoding='utf-8')))
    for r in data:
        if not r or not r[0].strip():
            continue
        key = r[0].strip()
        name_key = r[1].strip() if len(r) > 1 else ''
        iid = name_item.get(key)
        skus = shop_items.get(iid, []) if iid else []
        rows.append({
            '类别': label,
            'ID': key,
            '名称键': name_key,
            '中文名': zh_of(name_key) or zh_of(key),
            'itemId': iid if iid else '',
            '商城SKU数': len(skus),
            '获取途径': '商城购买' if skus else '活动/任务/赛季',
        })

print('%-10s %6s %8s %8s' % ('类别', '总数', '商城', '非商城'))
agg = collections.defaultdict(lambda: [0, 0, 0])
for r in rows:
    a = agg[r['类别']]
    a[0] += 1
    if r['商城SKU数']:
        a[1] += 1
    else:
        a[2] += 1
for k in agg:
    print('%-10s %6d %8d %8d' % (k, agg[k][0], agg[k][1], agg[k][2]))
tot = [sum(v[i] for v in agg.values()) for i in range(3)]
print('%-10s %6d %8d %8d' % ('合计', *tot))

out = os.path.join(BASE, 'codol_callsign_full_census.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['类别', 'ID', '名称键', '中文名', 'itemId',
                                       '商城SKU数', '获取途径'])
    w.writeheader()
    w.writerows(rows)
print('\nwrote', out, len(rows), 'rows')
named = sum(1 for r in rows if r['中文名'])
print('有中文名:', named, '/', len(rows))
