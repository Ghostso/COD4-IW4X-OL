# -*- coding: utf-8 -*-
"""Validate the 30-item pilot end-to-end offline, and prepare a ready-to-run
staging directory (nothing in the protected kit is touched)."""
import json, csv, os, io, sys, shutil, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

REF = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
STAGE = os.path.join(BASE, 'pilot30_stage')

sys.path.insert(0, REF)
import market_skus

entries = json.load(open(os.path.join(BASE, 'pilot30_catalog.json'), encoding='utf-8'))
print('pilot entries:', len(entries))

shaped = [{
    'id': e['Id'], 'productId': e['Item'], 'price': e['Price'],
    'currency': market_skus.CUR_CP, 'stackable': False, 'duration': 0,
    'name': '', 'category': e['Category'],
} for e in entries]

objs = [market_skus._sku_obj(s) for s in shaped]
total = sum(len(o) for o in objs)
print('encoded: %d objects, %d bytes total, %d bytes each'
      % (len(objs), total, len(objs[0])))
print('under 480KB reply budget:', total < 480 * 1024)

# staging dir with everything a run needs
if os.path.isdir(STAGE):
    shutil.rmtree(STAGE)
os.makedirs(STAGE)
shutil.copy2(os.path.join(BASE, 'pilot30_catalog.json'),
             os.path.join(STAGE, 'marketplace-catalog-merged.json'))

for flag, content in (('marketplace-skus.on', ''),
                      ('marketplace-skus-allow-unsafe.on', ''),
                      ('marketplace-skus-count.txt', '30\n'),
                      ('marketplace-catalog-merged.on', '')):
    with open(os.path.join(STAGE, flag), 'w', encoding='ascii') as fh:
        fh.write(content)

print('\nstaged in', STAGE)
for f in sorted(os.listdir(STAGE)):
    p = os.path.join(STAGE, f)
    print('  %-38s %d B' % (f, os.path.getsize(p)))
