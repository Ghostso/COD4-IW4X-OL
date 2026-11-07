# -*- coding: utf-8 -*-
"""Emit the supplementary marketplace catalogue for the playercard / emblem /
title trio, in the same schema as marketplace-catalog-client.json so it can be
merged into the server's catalog."""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'

rec = list(csv.DictReader(open(os.path.join(BASE, 'playercard_trio_skus.csv'), encoding='utf-8-sig')))

# existing catalog, to avoid duplicates and to learn the Category enum in use
cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
existing_ids = {int(e['Id']) for e in cat}

# currency column -> catalog Currency.  MEASURED against the 11194 (sku,
# price-column) pairs that exist in both tables:
#     column 2 -> Currency 1 (CP)   5154 agreements
#     column 5 -> Currency 2 (GP)   6029 agreements
#     (only 19 pairs disagree, 0.17%)
COL2CUR = {2: 1, 5: 2}

rows = []
skipped = 0
for r in rec:
    try:
        sid = int(r['sku'])
        iid = int(r['itemId'])
        amount = int(r['价格'])
        col = int(r['货币列'])
        days = int(r['期限天'])
    except (TypeError, ValueError):
        skipped += 1
        continue
    if sid in existing_ids:
        skipped += 1
        continue
    rows.append({
        'Id': sid,
        'Item': iid,
        'Currency': COL2CUR.get(col, 1),
        'Price': amount,
        'Category': 3,          # 3 = 外观 (cosmetic), same band as eye/han/ves
        'Stackable': False,
        'Grant': 1,
        'SelectedDays': days if days >= 0 else 0,
        '_label': r['类别'],
        '_name': r['内部名'],
    })

print('补充条目:', len(rows), ' 跳过(重复/无效):', skipped)
by = collections.Counter(r['_label'] for r in rows)
for k, v in by.most_common():
    print('  %-8s %d' % (k, v))

out_csv = os.path.join(BASE, 'marketplace_catalog_trio_supplement.csv')
with open(out_csv, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['Id', 'Item', 'Currency', 'Price', 'Category',
                                       'Stackable', 'Grant', 'SelectedDays',
                                       '_label', '_name'])
    w.writeheader()
    w.writerows(rows)

out_json = os.path.join(BASE, 'marketplace_catalog_trio_supplement.json')
with open(out_json, 'w', encoding='utf-8') as fh:
    json.dump([{k: v for k, v in r.items() if not k.startswith('_')} for r in rows],
              fh, ensure_ascii=False, indent=1)

print('\nwrote', out_csv)
print('wrote', out_json)

print('\n=== 样例（按类别各取 3 条）===')
for lab in ('名片背景', '徽章', '称号'):
    n = 0
    for r in rows:
        if r['_label'] != lab:
            continue
        print('  %-6s Id=%-6d Item=%-6d Cur=%d Price=%-6d Days=%-4d %s'
              % (lab, r['Id'], r['Item'], r['Currency'], r['Price'],
                 r['SelectedDays'], r['_name']))
        n += 1
        if n >= 3:
            break
