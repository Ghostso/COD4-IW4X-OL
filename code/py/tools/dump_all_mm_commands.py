"""把 6/14 里全部 mmstart 命令的完整文本打出来，对比两种形态。"""
import glob
import os
import re

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
logs = glob.glob(os.path.join(ROOT, '**', 'lobby_srv.log'), recursive=True)

HDR = re.compile(r'service=6 ver=\S+ task=14 declared=(\d+)')
PL = re.compile(r'payload\((\d+)\):\s*((?:[0-9a-f]{2} )+)')

seen = {}
for lp in logs:
    run = os.path.basename(os.path.dirname(os.path.dirname(lp)))
    lines = open(lp, encoding='utf-8', errors='replace').read().splitlines()
    for i, ln in enumerate(lines):
        if not HDR.search(ln):
            continue
        if i + 1 >= len(lines):
            continue
        m2 = PL.search(lines[i + 1])
        if not m2:
            continue
        raw = bytes.fromhex(m2.group(2).replace(' ', ''))
        j = raw.find(b'mm')
        if j < 0:
            continue
        txt = raw[j:].split(b'\x00')[0].decode('latin1', 'replace')
        key = txt
        seen.setdefault(key, []).append(run)

print('不同的 6/14 命令 %d 种:\n' % len(seen))
for txt, runs in sorted(seen.items(), key=lambda x: -len(x[1])):
    print('x%-4d (%d 个不同 run)' % (len(runs), len(set(runs))))
    print('   %s' % txt)
    print()
