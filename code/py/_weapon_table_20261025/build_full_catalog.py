# -*- coding: utf-8 -*-
"""Price every trio item and emit the complete marketplace catalogue."""
import json, csv, os, io, sys, collections, statistics, hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'

census = list(csv.DictReader(open(os.path.join(BASE, 'codol_callsign_catalog_final.csv'),
                                  encoding='utf-8-sig')))

# ---- 4-tier price model (from build 4tier script) ----
MODEL = {
    ('名片背景', 'CP', '永久'): [5003, 5003, 5003, 5003],
    ('名片背景', 'GP', '永久'): [100, 480, 753, 880],
    ('徽章',   'CP', '永久'): [1000, 5000, 5003, 5003],
    ('徽章',   'GP', '永久'): [480, 680, 880, 2480],
    ('称号',   'CP', '永久'): [5000, 5003, 5003, 5003],
    ('称号',   'GP', '永久'): [200, 675, 753, 10000],
    ('边框',   'GP', '永久'): [480, 680, 880, 2480],
    ('名牌',   'GP', '永久'): [200, 675, 753, 10000],
}
# period tiers derived from the permanent price (measured ratios:
# 7d ~ 1/8, 30d ~ 1/3, 90d ~ 4/5 of the permanent price)
DAY_RATIO = {7: 1 / 8.0, 14: 1 / 5.0, 30: 1 / 3.0, 90: 0.8}


def tier_of(item_id, label):
    """Deterministic tier assignment.  Without a rarity field in the data, we
    spread tiers by hashing the item id so each category shows a plausible mix
    rather than pricing everything the same."""
    h = int(hashlib.sha256(('%s:%d' % (label, item_id)).encode()).hexdigest()[:8], 16)
    return h % 4


existing = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
used_ids = {int(e['Id']) for e in existing}
next_id = max(used_ids) + 1

rows = []
for r in census:
    iid = r['itemId']
    lab = r['类别']
    if r['商城SKU数'] and int(r['商城SKU数']) > 0:
        continue                     # already sellable
    if not iid:
        continue
    iid_i = int(iid)
    t = tier_of(iid_i, lab)
    tiers = MODEL.get((lab, 'GP', '永久')) or MODEL[('称号', 'GP', '永久')]
    perm = tiers[t]
    cur = 'GP'
    rows.append({
        'Id': next_id, 'Item': iid_i, 'Currency': 2, 'Price': perm,
        'Category': 3, 'Stackable': False, 'Grant': 1, 'SelectedDays': 0,
        '_类别': lab, '_品质': ['普通', '稀有', '史诗', '传说'][t],
        '_名称': r['ID'], '_中文名': r['中文名'],
    })
    next_id += 1

print('新增可售条目:', len(rows))
by = collections.Counter(r['_品质'] for r in rows)
print('品质分布:', dict(by))
byc = collections.Counter(r['_类别'] for r in rows)
print('类别分布:', dict(byc))

out = os.path.join(BASE, 'marketplace_catalog_full_supplement.csv')
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['Id', 'Item', 'Currency', 'Price', 'Category',
                                       'Stackable', 'Grant', 'SelectedDays',
                                       '_类别', '_品质', '_名称', '_中文名'])
    w.writeheader()
    w.writerows(rows)

outj = os.path.join(BASE, 'marketplace_catalog_full_supplement.json')
with open(outj, 'w', encoding='utf-8') as fh:
    json.dump([{k: v for k, v in r.items() if not k.startswith('_')} for r in rows],
              fh, ensure_ascii=False, indent=1)
print('\nwrote', out)
print('wrote', outj)
print('\n=== 样例 ===')
for r in rows[:8]:
    print('  Id=%-6d Item=%-6d %-6s GP %-6d %-28s %s'
          % (r['Id'], r['Item'], r['_品质'], r['Price'], r['_名称'], r['_中文名'][:16]))
