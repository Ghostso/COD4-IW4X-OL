"""列出每个 run 的 mmstart 形态，并对照它是否连上了战斗服。

判据:
    - mmstart 带 g_gametype  -> 形态 A（可能能连）
    - mmstart 带 playlist 37 -> 形态 B（当前路径）
    - battle_srv/_battle_out 有 RX_/TX_ -> 连上了
"""
import glob
import os
import re

ROOT = r'D:\BaiduNetdiskDownload\mission'  # placeholder
ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'

rows = []
for d in sorted(glob.glob(os.path.join(ROOT, 'ONCE_*'))):
    kit = os.path.join(d, 'kit')
    if not os.path.isdir(kit):
        continue
    lp = os.path.join(kit, 'lobby_srv.log')
    if not os.path.isfile(lp):
        continue
    txt = open(lp, encoding='utf-8', errors='replace').read()

    mm = 'none'
    # 日志里有 "mmstart 完整命令" 行时常完整
    m = re.search(r'mmstart 完整命令: (.+)', txt)
    if m:
        cmd = m.group(1).strip()
        mm = 'A(g_gametype)' if 'g_gametype' in cmd else (
            'B(playlist37)' if 'playlist 37' in cmd else 'other')
    else:
        if 'g_gametype c' in txt:
            mm = 'A(g_gametype)'
        elif 'playlist 37' in txt:
            mm = 'B(playlist37)'

    # 战斗服是否收包
    rx = 0
    for bp in (os.path.join(kit, '_battle_out.txt'),
               os.path.join(kit, 'battle_srv.log')):
        if os.path.isfile(bp):
            b = open(bp, encoding='utf-8', errors='replace').read()
            rx += len(re.findall(r'RX_OOB|TX_NAT_REPLY|KEY_EXCHANGE_OK', b))
    rows.append((os.path.basename(d), mm, rx))

print('%-24s %-18s %s' % ('run', 'mmstart 形态', '战斗服事件数'))
print('-' * 60)
for name, mm, rx in rows:
    flag = ' ★连上' if rx else ''
    print('%-24s %-18s %d%s' % (name, mm, rx, flag))

print()
print('=== 按形态统计 ===')
from collections import defaultdict
agg = defaultdict(lambda: [0, 0])
for _, mm, rx in rows:
    agg[mm][0] += 1
    if rx:
        agg[mm][1] += 1
for mm, (n, ok) in sorted(agg.items()):
    print('  %-18s %3d 轮，其中 %d 轮战斗服有事件' % (mm, n, ok))
