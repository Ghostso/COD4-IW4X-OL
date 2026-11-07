# -*- coding: utf-8 -*-
"""Read UI_MARKET_ITEM_MENU_* values by walking the key/value stream in order.

Layout observed: [value] KEY NUL [padding] [value] KEY NUL ... i.e. each key is
followed by padding and then the NEXT key; the value that belongs to a key
appears BEFORE it.  So we pair each key with the CJK token immediately
preceding it.
"""
import io, sys, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\loc_post_gfx.zone'
d = open(ZONE, 'rb').read()

start = 0x0b3767
end = 0x0b4000
buf = d[start:end]

KEYRE = re.compile(rb'UI_MARKET_ITEM_MENU_([A-Z0-9_]+)\x00')
CJK = re.compile(rb'([\xb0-\xf7][\x40-\xfe]){1,8}')

results = []
for m in KEYRE.finditer(buf):
    key = m.group(1).decode()
    # look backwards from the key for the nearest CJK run
    p = m.start()
    seg = buf[max(0, p - 60):p]
    # strip trailing 0xff padding
    seg2 = seg.rstrip(b'\xff')
    best = None
    for c in CJK.finditer(seg2):
        best = c
    if best is None:
        results.append((key, '', ''))
        continue
    raw = best.group()
    try:
        txt = raw.decode('gbk')
        ok = all('\u4e00' <= ch <= '\u9fff' for ch in txt)
    except Exception:
        txt, ok = raw.hex(' '), False
    results.append((key, txt if ok else '<bad>', raw.hex(' ')))

print('%-28s %-14s %s' % ('MENU KEY', 'VALUE', 'BYTES'))
for k, v, hx in results:
    print('%-28s %-14s %s' % (k, v, hx))
