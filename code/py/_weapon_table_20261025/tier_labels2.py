# -*- coding: utf-8 -*-
"""Parse the four (five) market tier labels directly from the localize zone,
reading each key's value that follows it."""
import io, sys, json, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\loc_post_gfx.zone'
OUT = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\market_tier_labels.csv'
d = open(ZONE, 'rb').read()

KEYS = [b'UI_MARKET_TIER_LABEL_COMMON', b'UI_MARKET_TIER_LABEL_UNCOMMON',
        b'UI_MARKET_TIER_LABEL_RARE', b'UI_MARKET_TIER_LABEL_EPIC',
        b'UI_MARKET_TIER_LABEL_LEGENDARY']

print('%-34s %-10s %s' % ('KEY', 'VALUE', 'BYTES'))
rows = []
for k in KEYS:
    i = d.find(k)
    if i < 0:
        print('%-34s <not found>' % k.decode())
        continue
    p = i + len(k) + 1
    while p < len(d) and d[p] == 0xFF:
        p += 1
    e = d.find(b'\0', p, p + 64)
    v = d[p:e]
    try:
        t = v.decode('gbk')
        ok = all('\u4e00' <= ch <= '\u9fff' for ch in t)
    except Exception:
        t, ok = v.hex(' '), False
    print('%-34s %-10s %-16s %s' % (k.decode(), t, v.hex(' '),
                                    '' if ok else '<not-cjk>'))
    rows.append((k.decode(), t, v.hex(' ')))

with open(OUT, 'w', encoding='utf-8-sig', newline='') as fh:
    import csv
    w = csv.writer(fh)
    w.writerow(['key', 'value_zh', 'raw_hex'])
    w.writerows(rows)
print('\nwrote', OUT)
