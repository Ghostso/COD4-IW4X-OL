# -*- coding: utf-8 -*-
"""Locate the four tier-label keys in the localize zone and print each one's
immediate neighbourhood so the key/value pairing can be read by hand."""
import io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\loc_post_gfx.zone'
d = open(ZONE, 'rb').read()

KEYS = [b'UI_MARKET_TIER_LABEL_UNCOMMON', b'UI_MARKET_TIER_LABEL_RARE',
        b'UI_MARKET_TIER_LABEL_LEGENDARY', b'UI_MARKET_TIER_LABEL_EPIC']

for k in KEYS:
    i = d.find(k)
    print('===', k.decode(), 'at', hex(i))
    s = max(0, i - 32)
    e = min(len(d), i + len(k) + 40)
    c = d[s:e]
    for off in range(0, len(c), 16):
        row = c[off:off + 16]
        hx = ' '.join('%02x' % b for b in row)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        print('  %#08x %-47s %s' % (s + off, hx, asc))
    # decode the 1-3 tokens after the key
    p = i + len(k)
    while p < len(d) and d[p] == 0:
        p += 1
    toks = []
    while len(toks) < 3 and p < len(d):
        while p < len(d) and d[p] == 0xff:
            p += 1
        e2 = d.find(b'\0', p, p + 120)
        if e2 < 0:
            break
        v = d[p:e2]
        if not v:
            p = e2 + 1
            continue
        try:
            t = v.decode('gbk')
            valid = all('\u4e00' <= ch <= '\u9fff' for ch in t)
        except Exception:
            t, valid = v.hex(' '), False
        toks.append((t, valid, v.hex(' ')))
        p = e2 + 1
        if valid:
            break
    print('   -> next token:', toks[-1] if toks else None)
    print()
