# -*- coding: utf-8 -*-
"""Pick a 30-item pilot sample from the 30000-segment playercard ids, all three
kinds, and emit both the catalogue entries and a human-readable pilot list."""
import json, csv, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'

PRICE_CP = 2400
CURRENCY_CP = 1
CATEGORY = 1
PILOT_N = 30

rows = list(csv.DictReader(open(os.path.join(BASE, 'codol_callsign_catalog_final.csv'),
                                encoding='utf-8-sig')))
seg = [r for r in rows if r['itemId'] and 30000 <= int(r['itemId']) < 31000]
by_kind = collections.defaultdict(list)
for r in seg:
    by_kind[r['类别']].append(r)

# take 10 of each of the three main kinds, lowest itemId first
picked = []
for kind in ('名片背景', '徽章', '称号'):
    cand = sorted(by_kind[kind], key=lambda r: int(r['itemId']))
    picked.extend(cand[:PILOT_N // 3])

print('样张条目:', len(picked))
print('分类分布:', dict(collections.Counter(r['类别'] for r in picked)))

cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-merged.json'), encoding='utf-8'))
next_id = max(int(e['Id']) for e in cat) + 1

entries = []
for r in picked:
    entries.append({
        'Id': next_id, 'Item': int(r['itemId']), 'Currency': CURRENCY_CP,
        'Price': PRICE_CP, 'Category': CATEGORY, 'Stackable': False,
        'Grant': 1, 'SelectedDays': 0,
        '_类别': r['类别'], '_名称': r['ID'], '_中文名': r['中文名'],
    })
    next_id += 1

out = os.path.join(BASE, 'pilot30_catalog.json')
with open(out, 'w', encoding='utf-8') as fh:
    json.dump([{k: v for k, v in e.items() if not k.startswith('_')} for e in entries],
              fh, ensure_ascii=False, indent=1)

outcsv = os.path.join(BASE, 'pilot30_catalog.csv')
with open(outcsv, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['Id', 'Item', 'Currency', 'Price', 'Category',
                                       'Stackable', 'Grant', 'SelectedDays',
                                       '_类别', '_名称', '_中文名'])
    w.writeheader()
    w.writerows(entries)

print('\nwrote', out)
print('wrote', outcsv)
print('\n=== 样张清单 ===')
for e in entries:
    print('  Id=%-6d Item=%-6d %-6s %-26s %s'
          % (e['Id'], e['Item'], e['_类别'], e['_名称'], e['_中文名'][:22]))
