# -*- coding: utf-8 -*-
"""Call marketplace_store.load_catalog() without the swallowing try/except and
report the real failure."""
import sys, os, json, io, shutil, tempfile, traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

REF = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'

tmp = tempfile.mkdtemp(prefix='catload_')
for n in ('marketplace_store.py', 'codol_crypto.py', 'marketplace-catalog-client.json'):
    shutil.copy2(os.path.join(REF, n), os.path.join(tmp, n))
print('tmp', tmp)

sys.path.insert(0, tmp)
import marketplace_store as ms

print('catalog_path() =', ms.catalog_path())
print('exists:', os.path.exists(ms.catalog_path()))

try:
    cat = ms.load_catalog()
    print('load_catalog OK ->', len(cat), 'entries')
    k = sorted(cat)[:3]
    for i in k:
        print('  ', cat[i])
except Exception:
    print('load_catalog RAISED:')
    traceback.print_exc()

shutil.rmtree(tmp, ignore_errors=True)
