"""逐行扫描日志，提取 service=6 各 task 的 payload。"""
import glob
import os
import re

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
logs = glob.glob(os.path.join(ROOT, '**', 'lobby_srv.log'), recursive=True)

HDR = re.compile(r'service=6 ver=\S+ task=(\d+) declared=(\d+)')
PL = re.compile(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)')

pats = {}
for lp in logs:
    lines = open(lp, encoding='utf-8', errors='replace').read().splitlines()
    for i, ln in enumerate(lines):
        m = HDR.search(ln)
        if not m:
            continue
        task = int(m.group(1))
        if i + 1 >= len(lines):
            continue
        m2 = PL.search(lines[i + 1])
        if not m2:
            continue
        raw = bytes.fromhex(m2.group(2).replace(' ', ''))
        pats.setdefault(task, {})
        pats[task][raw] = pats[task].get(raw, 0) + 1

print('service=6 的 task: %s' % sorted(pats))
for task in sorted(pats):
    print()
    print('=== 6/%d  (%d 种) ===' % (task, len(pats[task])))
    for raw, cnt in sorted(pats[task].items(), key=lambda x: -x[1])[:5]:
        print('  x%-4d %s' % (cnt, raw[:100].hex()))
        if b'mmbook' in raw or b'mmstart' in raw:
            j = raw.find(b'mm')
            print('         %r' % raw[j:j + 90])
