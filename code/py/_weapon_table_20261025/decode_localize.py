# -*- coding: utf-8 -*-
"""Decode the CODOL localize asset: alternating NUL-terminated key/value pairs.

The Chinese payload is GBK. Walks the string region and pairs
KEY, VALUE, KEY, VALUE ... using the PLAYERCARDS_*/SF_UI_* key shapes.
"""
import re, io, sys, csv, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ZONE = sys.argv[1] if len(sys.argv) > 1 else \
    r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\loc_post_gfx.zone'
OUT = sys.argv[2] if len(sys.argv) > 2 else \
    r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025\localize_zh.csv'

d = open(ZONE, 'rb').read()
print('zone bytes', len(d))

KEY_RE = re.compile(rb'^[A-Z][A-Z0-9_]{3,80}$')

# collect all NUL-terminated tokens with offsets
toks = []
i = 0
n = len(d)
while i < n:
    j = d.find(b'\0', i)
    if j < 0:
        break
    toks.append((i, d[i:j]))
    i = j + 1

print('tokens', len(toks))

pairs = []
k = 0
while k < len(toks) - 1:
    off, t = toks[k]
    if KEY_RE.match(t) and len(t) > 6:
        voff, v = toks[k + 1]
        # strip leading 0xFF alignment padding
        v = v.lstrip(b'\xff')
        if v and not KEY_RE.match(v) and len(v) < 400:
            try:
                zh = v.decode('gbk')
            except UnicodeDecodeError:
                try:
                    zh = v.decode('utf-8')
                except UnicodeDecodeError:
                    zh = v.decode('latin-1')
            pairs.append((t.decode('ascii', 'replace'), zh, hex(off)))
            k += 2
            continue
    k += 1

# de-duplicate: keep first occurrence per key
seen = {}
for key, val, off in pairs:
    seen.setdefault(key, val)

print('key/value pairs', len(pairs), 'unique keys', len(seen))
for key in ('PLAYERCARDS_PCB_DEFAULT_NAME', 'SF_UI_BADGE_XPBOOST_NAME'):
    print('  %-32s -> %s' % (key, seen.get(key)))

with open(OUT, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['key', 'text_zh'])
    for key in sorted(seen):
        w.writerow([key, seen[key]])
print('wrote', OUT)
