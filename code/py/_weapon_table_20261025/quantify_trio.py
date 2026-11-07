# -*- coding: utf-8 -*-
"""Quantify exactly what is missing for the playercard / emblem / title trio."""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'

cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
cat_items = {int(e['Item']) for e in cat}

# 1) 三件套 itemId -> 名字（来自 MarketplaceSkus）
mk = json.load(open(r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json', encoding='utf-8'))
PREFIX = {'pcb_': '名片背景', 'pci_': '徽章', 'pct_': '称号',
          'pcf_': '边框', 'pcn_': '名牌', 'pcai_': '动态图标',
          'pcab_': '动态背景', 'pcaf_': '动态边框', 'pca_': '其他名片'}
trio = collections.defaultdict(dict)
for p in mk['products']:
    for g in p.get('grants', []):
        nm = g.get('name', '')
        iid = g.get('itemId')
        if not iid:
            continue
        for pre, label in PREFIX.items():
            if nm.startswith(pre):
                trio[label].setdefault(int(iid), nm)
                break

print('=== 三件套 itemId 覆盖情况 ===')
print('%-10s %8s %8s %8s' % ('类别', 'itemId数', '在目录里', '缺失'))
total = miss_total = 0
for label in ('名片背景', '徽章', '称号', '边框', '名牌', '动态图标', '动态背景', '动态边框'):
    ids = trio.get(label, {})
    n = len(ids)
    have = sum(1 for i in ids if i in cat_items)
    print('%-10s %8d %8d %8d' % (label, n, have, n - have))
    total += n
    miss_total += n - have
print('%-10s %8d %8d %8d' % ('合计', total, total - miss_total, miss_total))

# 2) 目录里有哪些 itemId 段是空的
print('\n=== 目录 Item 段分布 ===')
band = collections.Counter(i // 10000 * 10000 for i in cat_items)
gaps = [b for b in range(0, 70000, 10000) if band.get(b, 0) == 0]
print('完全空白的万位段:', gaps)
for b in range(0, 70000, 10000):
    print('  %6d..  %6d  %s' % (b, b + 9999, band.get(b, 0)))

# 3) 三件套 itemId 落在哪些段
print('\n=== 三件套 itemId 所在段 ===')
alltrio = [i for d in trio.values() for i in d]
tb = collections.Counter(i // 10000 * 10000 for i in alltrio)
for b in sorted(tb):
    print('  %6d..  %6d  %d 个  (目录里有 %d)'
          % (b, b + 9999, tb[b], sum(1 for i in alltrio if i // 10000 * 10000 == b and i in cat_items)))

# 4) 导出缺失清单
out = os.path.join(BASE, 'playercard_emblem_title_items.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['类别', 'itemId', '内部名', '在商品目录中'])
    for label in trio:
        for iid, nm in sorted(trio[label].items()):
            w.writerow([label, iid, nm, 'yes' if iid in cat_items else 'NO'])
print('\nwrote', out)
