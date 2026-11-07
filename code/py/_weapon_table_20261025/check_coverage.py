# -*- coding: utf-8 -*-
"""Coverage check: do the recovered SKUs cover the 104 unowned trio items,
and how does this compare with marketplace-catalog-client.json?"""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'

rec = list(csv.DictReader(open(os.path.join(BASE, 'playercard_trio_skus.csv'), encoding='utf-8-sig')))
rec_items = {int(r['itemId']) for r in rec}

unowned = list(csv.DictReader(open(os.path.join(BASE, 'playercard_trio_unowned.csv'), encoding='utf-8-sig')))
un_ids = {int(r['itemId']) for r in unowned}

audit = list(csv.DictReader(open(os.path.join(BASE, 'playercard_trio_audit.csv'), encoding='utf-8-sig')))
all_ids = {int(r['itemId']) for r in audit}

cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
cat_items = {int(e['Item']) for e in cat}

print('三件套总条目      :', len(all_ids))
print('MarketplaceSkus 覆盖:', len(rec_items & all_ids), '/', len(all_ids))
print('catalog-client 覆盖 :', len(cat_items & all_ids), '/', len(all_ids))
print()
print('未拥有条目        :', len(un_ids))
print('  被 MarketplaceSkus 覆盖:', len(rec_items & un_ids))
print('  被 catalog-client 覆盖 :', len(cat_items & un_ids))
print()
print('合并后覆盖率:', len((rec_items | cat_items) & all_ids), '/', len(all_ids))

still = sorted(un_ids - rec_items)
print('\n仍无 SKU 的未拥有条目:', len(still))
for r in unowned:
    if int(r['itemId']) in still:
        print('  %-6s %-6s %-26s %s' % (r['类别'], r['itemId'], r['内部名'], r['中文名'][:18]))
