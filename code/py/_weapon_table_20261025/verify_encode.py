# -*- coding: utf-8 -*-
"""Offline check: encode the new trio catalogue exactly the way the server would
and report object count, total bytes, and any encoding failure.

No game client, no server, no protected file touched.
"""
import sys, os, json, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

REF = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT'
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
sys.path.insert(0, REF)

import codol_crypto as cc
import market_skus

print('market_skus from', market_skus.__file__)

entries = json.load(open(os.path.join(BASE, 'marketplace_catalog_trio_2400cp.json'), encoding='utf-8'))
print('entries to encode:', len(entries))

# The server path uses catalog_entries() -> dicts with these keys.
# Reshape our inventory-shaped rows into that shape.
shaped = [{
    'id': e['Id'],
    'productId': e['Item'],
    'price': e['Price'],
    'currency': market_skus.CUR_CP,
    'stackable': bool(e['Stackable']),
    'duration': int(e['SelectedDays']),
    'name': '',
    'category': int(e['Category']),
} for e in entries]

ok = 0
fail = 0
total = 0
sizes = []
first_fail = None
for e in shaped:
    try:
        obj = market_skus._sku_obj(e)
        sizes.append(len(obj))
        total += len(obj)
        ok += 1
    except Exception as ex:
        fail += 1
        if first_fail is None:
            first_fail = (e, ex)

print('encoded OK :', ok)
print('failed     :', fail)
if first_fail:
    print('first failure:', first_fail[1], first_fail[0])

if sizes:
    print('object size min/max/avg: %d / %d / %.1f'
          % (min(sizes), max(sizes), sum(sizes) / len(sizes)))
    print('total payload: %d bytes (%.1f KB)' % (total, total / 1024.0))
    print('reply budget in code: 480 KB  ->  %s'
          % ('OK' if total < 480 * 1024 else 'OVER BUDGET'))

    # What the real reply looks like: build_task_reply_objects wraps it
    print()
    print('reply framing overhead: each object gets a 0x08 tag + u32 length (5 B)')
    framed = total + 5 * len(sizes)
    print('framed payload: %d bytes (%.1f KB)' % (framed, framed / 1024.0))
