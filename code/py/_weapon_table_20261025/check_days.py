# -*- coding: utf-8 -*-
"""Check the marketplace catalog entries for the categories the user reports:
weapons (7/30/permanent) vs namecards (playercards)."""
import json, csv, io, sys, collections, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
print('catalog entries', len(cat))

by_cat = collections.Counter(e['Category'] for e in cat)
print('\nCategory distribution:')
for c, n in sorted(by_cat.items()):
    print('  Category %d : %d entries' % (c, n))

by_days = collections.Counter(e['SelectedDays'] for e in cat)
print('\nSelectedDays distribution:')
for d, n in sorted(by_days.items()):
    print('  %4d days : %d entries' % (d, n))

print('\nGrouping one Item that has multiple tiers (7/30/perm):')
by_item = collections.defaultdict(list)
for e in cat:
    by_item[int(e['Item'])].append(e)
multi = [(it, v) for it, v in by_item.items() if len(v) >= 3]
print('items with >=3 SKUs:', len(multi))
for it, v in sorted(multi)[:5]:
    print('  Item %d:' % it)
    for e in sorted(v, key=lambda x: x['Id']):
        print('     Id=%-7d Currency=%d Price=%-6d Cat=%d Days=%-5d Stackable=%s'
              % (e['Id'], e['Currency'], e['Price'], e['Category'],
                 e['SelectedDays'], e['Stackable']))

print('\nStackable by Category:')
for c in sorted(by_cat):
    rows = [e for e in cat if e['Category'] == c]
    st = sum(1 for e in rows if e['Stackable'])
    print('  Cat %d: %d rows, %d stackable' % (c, len(rows), st))
