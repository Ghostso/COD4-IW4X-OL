# -*- coding: utf-8 -*-
"""Produce the definitive audit of what is and is not available for the
playercard / emblem / title trio."""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'

cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
cat_items = collections.defaultdict(list)
for e in cat:
    cat_items[int(e['Item'])].append(e)

mk = json.load(open(r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json', encoding='utf-8'))
PREFIX = [('pcb_', '名片背景'), ('pci_', '徽章'), ('pct_', '称号'),
          ('pcf_', '边框'), ('pcn_', '名牌'), ('pcai_', '动态图标'),
          ('pcab_', '动态背景'), ('pcaf_', '动态边框')]
trio = collections.defaultdict(dict)
for p in mk['products']:
    for g in p.get('grants', []):
        nm, iid = g.get('name', ''), g.get('itemId')
        if not iid:
            continue
        for pre, label in PREFIX:
            if nm.startswith(pre):
                trio[label].setdefault(int(iid), nm)
                break

# item -> localize key candidates from the item table (our decoded items csv)
itemcsv = list(csv.DictReader(open(os.path.join(BASE, 'codol_items_3_19.csv'), encoding='utf-8-sig')))
zh = {}
for r in csv.DictReader(open(os.path.join(BASE, 'localize_zh.csv'), encoding='utf-8-sig')):
    zh[r['key']] = r['text_zh']


def zh_of(name):
    """name is like pcb_amorphous01 -> PLAYERCARDS_PCB_AMORPHOUS01_NAME"""
    up = name.upper()
    for k in (up + '_NAME', 'PLAYERCARDS_' + up + '_NAME'):
        if k in zh:
            return zh[k]
    return ''


rows = []
for label, items in trio.items():
    for iid, nm in sorted(items.items()):
        skus = cat_items.get(iid, [])
        rows.append({
            '类别': label,
            'itemId': iid,
            '内部名': nm,
            '中文名': zh_of(nm),
            '目录SKU数': len(skus),
            '货币档': ','.join(sorted({str(s['Currency']) for s in skus})) if skus else '',
            '期限档': ','.join(str(s['SelectedDays']) for s in sorted(skus, key=lambda x: x['SelectedDays'])) if skus else '',
            '价格': ','.join(str(s['Price']) for s in sorted(skus, key=lambda x: x['SelectedDays'])) if skus else '',
        })

out = os.path.join(BASE, 'playercard_trio_audit.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['类别', 'itemId', '内部名', '中文名',
                                       '目录SKU数', '货币档', '期限档', '价格'])
    w.writeheader()
    w.writerows(rows)

print('wrote', out, len(rows), 'rows')
print()
print('%-10s %6s %6s' % ('类别', '总数', '有SKU'))
agg = collections.defaultdict(lambda: [0, 0])
for r in rows:
    a = agg[r['类别']]
    a[0] += 1
    if r['目录SKU数']:
        a[1] += 1
for k in sorted(agg):
    print('%-10s %6d %6d' % (k, agg[k][0], agg[k][1]))

named = sum(1 for r in rows if r['中文名'])
print('\n有中文名的条目:', named, '/', len(rows))
print('\n样例（前 8 条有中文名的）:')
n = 0
for r in rows:
    if r['中文名']:
        print('  %-6s %-6d %-30s %s' % (r['类别'], r['itemId'], r['内部名'], r['中文名']))
        n += 1
        if n >= 8:
            break
