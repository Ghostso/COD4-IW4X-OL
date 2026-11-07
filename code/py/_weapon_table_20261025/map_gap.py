# -*- coding: utf-8 -*-
"""Map the gaps in the marketplace catalog's Item-id space, and check where the
playercard / emblem / title item ids fall."""
import json, os, io, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
cat = json.load(open(os.path.join(KIT, 'marketplace-catalog-client.json'), encoding='utf-8'))
items = sorted({int(e['Item']) for e in cat})

print('distinct catalog Items:', len(items))
print('range', items[0], '..', items[-1])

# density per 1000-band
band = collections.Counter(i // 1000 * 1000 for i in items)
print('\nItem-id bands (count per 1000):')
for b in range(0, 61):
    k = b * 1000
    n = band.get(k, 0)
    bar = '#' * min(60, n // 20)
    print('  %5d  %5d  %s' % (k, n, bar))

# playercard ids from MarketplaceSkus
mk = json.load(open(r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\assets\backend\1004\MarketplaceSkus.json', encoding='utf-8'))
pc = {}
for p in mk['products']:
    for g in p.get('grants', []):
        nm = g.get('name', '')
        if g.get('itemId') and nm.startswith(('pcb_', 'pci_', 'pct_', 'pcf_', 'pcn_', 'pcai_', 'pcab_', 'pcaf_')):
            pc.setdefault(int(g['itemId']), nm)
print('\nplayercard itemIds in MarketplaceSkus:', len(pc))
ids = sorted(pc)
print('range', ids[0], '..', ids[-1])
inband = collections.Counter(i // 1000 * 1000 for i in ids)
print('their bands:', sorted(inband.items())[:20])
present = sum(1 for i in ids if i in set(items))
print('of those, present in catalog:', present)
