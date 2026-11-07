# -*- coding: utf-8 -*-
"""Create an isolated pilot kit: a copy of the GOLDEN kit with the SKU-page
modules, the 30-item catalogue and the gate flags added.

The GOLDEN kit itself is never written to.
"""
import json, os, io, sys, shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

GOLDEN = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
REF = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = os.path.join(BASE, 'PILOT30_KIT')

if os.path.isdir(KIT):
    shutil.rmtree(KIT)
shutil.copytree(GOLDEN, KIT)
print('copied GOLDEN ->', KIT)

# 1. modules the lobby server imports
for n in ('market_skus.py', '_sku_schema_as.py'):
    src = os.path.join(REF, n)
    if not os.path.exists(src):
        raise SystemExit('missing in REF: ' + n)
    shutil.copy2(src, os.path.join(KIT, n))
    print('  + %-24s %d B' % (n, os.path.getsize(src)))

# 2. the 30-item catalogue, replacing the merged one the store reads
pilot = json.load(open(os.path.join(BASE, 'pilot30_catalog.json'), encoding='utf-8'))
dst = os.path.join(KIT, 'marketplace-catalog-merged.json')
json.dump(pilot, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
print('  + marketplace-catalog-merged.json -> %d entries' % len(pilot))

# 3. gate flags
for flag, content in (('marketplace-skus.on', ''),
                      ('marketplace-skus-allow-unsafe.on', ''),
                      ('marketplace-skus-count.txt', '30\n')):
    with open(os.path.join(KIT, flag), 'w', encoding='ascii') as fh:
        fh.write(content)
    print('  + %s' % flag)

# 4. the baseline manifest must match the new kit (the launcher verifies it)
CORE = [
    "run_all.py", "nt10.py", "lobby_server.py", "fake_auth_tls.py",
    "codol_crypto.py", "write_dwauth.py", "make_local_ca.ps1", "battle_server.py",
    "_rsa.txt", "_leaf2.cer", "_ca.pem", "_ca.cer", "_leaf2.key",
    "_leaf2_chain.pem", "lobby_spec.txt", "tas_spec.txt", "patch_spec.txt",
    "late_spec.txt", "player-account.json", "marketplace-inventory.json",
    "marketplace-catalog-merged.json", "marketplace-catalog-client.json",
    "marketplace-catalog.json", "firingrange-gamestate.bin",
    "firingrange-session.enabled", "firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH",
    "playlists-include-pve.on", "ready_push.on", "mirror_predicted.on",
    "marketplace-catalog-merged.on", "marketplace-catalog-client.on",
    "marketplace-currency-lenient.on", "catalog-include-sku-table.on",
    "market_skus.py", "_sku_schema_as.py",
    "marketplace-skus.on", "marketplace-skus-allow-unsafe.on",
    "marketplace-skus-count.txt",
]


def sha(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest().upper()


man = {n: {'size': os.path.getsize(os.path.join(KIT, n)),
           'sha256': sha(os.path.join(KIT, n))}
       for n in CORE if os.path.isfile(os.path.join(KIT, n))}
json.dump(man, open(os.path.join(KIT, '_run_once_hashes.json'), 'w', encoding='utf-8'),
          indent=2)
print('  + _run_once_hashes.json -> %d files' % len(man))

print('\npilot kit ready:', KIT)
