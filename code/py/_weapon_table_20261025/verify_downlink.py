# -*- coding: utf-8 -*-
"""End-to-end offline check of the catalogue downlink:
build the merged catalogue, call market_skus.catalog_entries() and
build_sku_page() exactly as lobby_server.py does, and report what comes out.
"""
import sys, os, json, io, shutil, tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

REF = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'

# Work in a temp dir so nothing protected is touched.
tmp = tempfile.mkdtemp(prefix='skupage_')
print('temp kit dir:', tmp)
for n in ('market_skus.py', '_sku_schema_as.py', 'codol_crypto.py',
          'marketplace_store.py', 'marketplace-catalog-client.json',
          'marketplace-catalog-merged.json', 'marketplace-catalog.json',
          'marketplace-catalog-merged.on'):
    src = os.path.join(REF, n)
    if not os.path.exists(src):
        src = os.path.join(KIT, n)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(tmp, n))

# Marketplace store reads marketplace-catalog-merged.json when its .on flag is
# present, else marketplace-catalog.json.  Patch whichever it picks.
sys.path.insert(0, tmp)
import marketplace_store as _ms_probe
CATFILE = _ms_probe.catalog_path()
print('store will read:', os.path.basename(CATFILE))
cat = json.load(open(CATFILE, encoding='utf-8'))
supp = json.load(open(os.path.join(BASE, 'marketplace_catalog_trio_2400cp.json'), encoding='utf-8'))
before = len(cat)
cat.extend(supp)
json.dump(cat, open(CATFILE, 'w', encoding='utf-8'))
print('catalogue: %d -> %d entries' % (before, len(cat)))

sys.path.insert(0, tmp)
import market_skus
print('market_skus loaded from', market_skus.__file__)

ms = market_skus
entries = ms.catalog_entries(limit=2000)
print('\ncatalog_entries(limit=2000) ->', len(entries))
print('first entry:', entries[0] if entries else None)

objs = ms.build_sku_page(entries)
print('build_sku_page ->', len(objs), 'objects, %d bytes'
      % sum(len(o) for o in objs))

# how many of ours survived the de-dup in catalog_entries?
ours = {e['Id'] for e in supp}
kept = sum(1 for e in entries if e['id'] in ours)
print('our entries kept after de-dup:', kept, '/', len(ours))

shutil.rmtree(tmp, ignore_errors=True)
