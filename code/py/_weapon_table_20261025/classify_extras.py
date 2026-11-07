# -*- coding: utf-8 -*-
"""Classify the extra (merged-only) catalog entries: which are real playercard
SKUs and which are memory-garbage noise."""
import json, os, csv, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'

plain = json.load(open(os.path.join(KIT, 'marketplace-catalog.json'), encoding='utf-8'))
merged = json.load(open(os.path.join(KIT, 'marketplace-catalog-merged.json'), encoding='utf-8'))
seen = {(e['Id'], e['Item']) for e in plain}
extra = [e for e in merged if (e['Id'], e['Item']) not in seen]

# playercard item ids
mk = json.load(open(r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json', encoding='utf-8'))
pc = {}
for p in mk['products']:
    for g in p.get('grants', []):
        nm = g.get('name', '')
        if g.get('itemId') and nm.startswith(('pcb_', 'pci_', 'pct_', 'pcf_', 'pcn_', 'pcai_', 'pcab_', 'pcaf_')):
            pc.setdefault(int(g['itemId']), nm)


def sane(e):
    """Heuristics that separate real catalog rows from memory-scan noise."""
    i, it, p = int(e['Id']), int(e['Item']), int(e['Price'])
    if abs(i - it) <= 8:
        return False
    if p and (p & (p - 1)) == 0 and p > 1024:
        return False
    if it > 100000:
        return False
    return True


good = [e for e in extra if sane(e)]
print('extra entries:', len(extra), ' sane:', len(good), ' noise:', len(extra) - len(good))

print('\n--- sane extras in the blank 30000-59999 band ---')
band = [e for e in good if 30000 <= int(e['Item']) < 60000]
print('count:', len(band))
for e in sorted(band, key=lambda x: int(x['Item'])):
    it = int(e['Item'])
    nm = pc.get(it, '')
    print('  Id=%-6d Item=%-6d Cur=%d Price=%-7d Cat=%d Days=%-4d  %s'
          % (e['Id'], it, e['Currency'], e['Price'], e['Category'],
             e['SelectedDays'], nm or '<非名片>' if not nm else nm))

out = os.path.join(BASE, 'recovered_playercard_sku_candidates.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['Id', 'Item', 'Currency', 'Price', 'Category', 'Stackable',
                'Grant', 'SelectedDays', 'item_name', 'source'])
    for e in sorted(band, key=lambda x: int(x['Item'])):
        w.writerow([e['Id'], e['Item'], e['Currency'], e['Price'], e['Category'],
                    e['Stackable'], e['Grant'], e['SelectedDays'],
                    pc.get(int(e['Item']), ''), 'merged-extra'])
print('\nwrote', out)
