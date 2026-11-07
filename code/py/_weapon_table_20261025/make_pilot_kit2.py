# -*- coding: utf-8 -*-
"""PILOT30_KIT_V2: rebuild the pilot kit from the CURRENT GOLDEN kit.

Why V2: the first PILOT30_KIT was copied on 2026-10-26 14:24, when GOLDEN still
held the 76410-byte lobby_server.py.  GOLDEN moved to the 88162-byte version on
2026-10-27 21:04 (the one that actually starts codol_battle_server.exe), so the
old kit fails run_frozen_chain_once.py's "unique battle server" assertion.

Nothing in GOLDEN or REF_LOBBY_KIT is written to.
"""
import json, os, io, sys, shutil, stat, hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

GOLDEN = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019'
REF = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
KIT = os.path.join(BASE, sys.argv[1] if len(sys.argv) > 1 else 'PILOT30_KIT_V2')

if os.path.isdir(KIT):
    raise SystemExit('refusing to overwrite existing kit: ' + KIT)
shutil.copytree(GOLDEN, KIT)
print('copied GOLDEN ->', KIT)


def clear_readonly(root):
    for dp, dns, fns in os.walk(root):
        for n in fns:
            p = os.path.join(dp, n)
            try:
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass


clear_readonly(KIT)

# 1. modules the lobby server imports
#    marketplace_store.py is the one that actually serves the catalogue,
#    inventory and purchases; the GOLDEN kit has never carried it.
for n, src in (('market_skus.py', os.path.join(REF, 'market_skus.py')),
               ('_sku_schema_as.py', os.path.join(REF, '_sku_schema_as.py')),
               ('marketplace_store.py',
                r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_LOCAL_CHAIN\marketplace_store.py')):
    if not os.path.exists(src):
        raise SystemExit('missing source: ' + src)
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
    p = os.path.join(KIT, flag)
    with open(p, 'w', encoding='ascii') as fh:
        fh.write(content)
    os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
    print('  + %s' % flag)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest().upper()


# 4. baseline manifest over the launcher's CORE list (kept in sync by hand)
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
    "client_movement.on", "omit_viewangles.on",
    "marketplace-catalog-merged.on", "marketplace-catalog-client.on",
    "marketplace-currency-lenient.on", "catalog-include-sku-table.on",
    "playlist_resolver.py", "dynamic_gamestate.py", "codol_battle_server.exe",
    "match_state_observer.py",
    "marketplace_store.py", "market_skus.py", "_sku_schema_as.py",
    "marketplace-skus.on", "marketplace-skus-allow-unsafe.on",
    "marketplace-skus-count.txt",
]
man = {n: {'size': os.path.getsize(os.path.join(KIT, n)),
           'sha256': sha(os.path.join(KIT, n))}
       for n in CORE if os.path.isfile(os.path.join(KIT, n))}
missing = [n for n in CORE if not os.path.isfile(os.path.join(KIT, n))]
mp = os.path.join(KIT, '_run_once_hashes.json')
json.dump(man, open(mp, 'w', encoding='utf-8'), indent=2)
os.chmod(mp, stat.S_IWRITE | stat.S_IREAD)
print('  + _run_once_hashes.json -> %d files' % len(man))
if missing:
    print('  (absent in GOLDEN, therefore unverified): ' + ', '.join(missing))

print('\npilot kit v2 ready:', KIT)
