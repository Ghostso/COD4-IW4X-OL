# -*- coding: utf-8 -*-
"""Read UI_MARKET_ITEM_MENU_* values byte-exactly, without the misaligning
runner.  For each key, print the bytes that follow it."""
import io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\loc_post_gfx.zone'
d = open(ZONE, 'rb').read()

KEYS = ['PLAYERCARD', 'PCB', 'PCI', 'PCT', 'PCF', 'PCN',
        'WEA', 'CAT', 'CHARACTER', 'EMO', 'PERK', 'BUNDLE']

for k in KEYS:
    key = ('UI_MARKET_ITEM_MENU_%s' % k).encode()
    i = d.find(key)
    if i < 0:
        print('%-40s <not found>' % key.decode())
        continue
    p = i + len(key) + 1
    # skip 0xff padding
    while p < len(d) and d[p] == 0xFF:
        p += 1
    e = d.find(b'\0', p, p + 80)
    v = d[p:e]
    try:
        t = v.decode('gbk')
        ok = all('\u4e00' <= ch <= '\u9fff' for ch in t) and len(t) <= 12
    except Exception:
        t, ok = v.hex(' '), False
    print('%-40s %-14s %-18s %s'
          % (key.decode(), t if ok else '<bad>', v.hex(' '),
             '' if ok else 'next-key follows'))
