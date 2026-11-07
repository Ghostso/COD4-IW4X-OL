# -*- coding: utf-8 -*-
"""Search project evidence for a captured retail gamestate configstring map that
covers the CS_WEAPONS window (5362+)."""
import json, os, glob, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

ROOTS = [
    r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\_extracted',
    r'D:\BaiduNetdiskDownload\使命召唤OL\_t2_5_evidence_run2',
    r'D:\BaiduNetdiskDownload\使命召唤OL\_t2_5_stageD_evidence',
    r'D:\BaiduNetdiskDownload\使命召唤OL\_rev_analysis',
    r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\WEAPON_READ_20261022',
]


def walk(o, path=''):
    if isinstance(o, dict):
        keys = list(o.keys())
        num = [k for k in keys if str(k).isdigit()]
        if len(num) >= 200:
            ints = sorted(int(k) for k in num)
            inwin = [k for k in ints if 5362 <= k <= 6100]
            yield (path, len(ints), ints[0], ints[-1], len(inwin))
        for k, v in o.items():
            yield from walk(v, path + '/' + str(k)[:40])
    elif isinstance(o, list):
        for i, v in enumerate(o[:400]):
            yield from walk(v, path + '[%d]' % i)


for root in ROOTS:
    for p in glob.glob(os.path.join(root, '**', '*.json'), recursive=True):
        if os.path.getsize(p) > 40_000_000:
            continue
        try:
            j = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        for hit in walk(j):
            print(p, hit)
