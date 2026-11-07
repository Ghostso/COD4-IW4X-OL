# -*- coding: utf-8 -*-
"""Scan every lobby/server log for actual purchase task hits (154 / 131) and
SKU failures."""
import os, io, sys, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'

PATTERNS = [
    (re.compile(rb'154\b'), 'task154(purchaseSkus)'),
    (re.compile(rb'131\b'), 'task131'),
    (re.compile(rb'purchase'), 'purchase'),
    (re.compile(rb'unknown_skus'), 'unknown_skus'),
    (re.compile('购买'.encode('utf-8')), 'cn-purchase'),
    (re.compile('购买'.encode('gbk')), 'cn-purchase-gbk'),
    (re.compile('购买'.encode('gb18030')), 'cn-purchase-gb18030'),
]

found = {}
for dp, dn, fn in os.walk(ROOT):
    if 'mkt_assets' in dp:
        continue
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
        for rx, label in PATTERNS:
            if rx.search(d):
                found.setdefault(label, []).append(p)

for label, paths in found.items():
    print('%-22s %d files' % (label, len(paths)))
    for p in paths[:4]:
        print('     ', p)
