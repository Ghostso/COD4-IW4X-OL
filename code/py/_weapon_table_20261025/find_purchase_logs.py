# -*- coding: utf-8 -*-
"""Find run logs that mention marketplace purchase activity."""
import os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
PATS = [b'purchase', b'marketplace 80', b'unknown_skus',
        '购买'.encode('utf-8'), '购买'.encode('gbk')]

hits = []
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        if not f.endswith(('.log', '.txt')):
            continue
        p = os.path.join(dp, f)
        try:
            if os.path.getsize(p) > 30_000_000:
                continue
            d = open(p, 'rb').read()
        except Exception:
            continue
        for pat in PATS:
            if pat in d:
                hits.append((p, len(d)))
                break

print('files with purchase references:', len(hits))
for p, n in hits[:30]:
    print('  %9d  %s' % (n, p))
