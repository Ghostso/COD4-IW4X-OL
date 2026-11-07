# -*- coding: utf-8 -*-
"""Dump a wide window around the UI_MARKET_ITEM_MENU_* key block so the
key/value layout can be read directly."""
import io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\loc_post_gfx.zone'
d = open(ZONE, 'rb').read()

i = d.find(b'UI_MARKET_ITEM_MENU_')
print('first MENU key at', hex(i))
start = max(0, i - 64)
end = min(len(d), i + 1400)
c = d[start:end]
for off in range(0, len(c), 16):
    row = c[off:off + 16]
    hx = ' '.join('%02x' % b for b in row)
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
    # try gbk for CJK runs
    print('%#08x %-47s %s' % (start + off, hx, asc))
