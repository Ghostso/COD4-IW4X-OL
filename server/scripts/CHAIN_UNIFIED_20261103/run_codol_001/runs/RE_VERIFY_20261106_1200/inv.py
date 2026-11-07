# -*- coding: utf-8 -*-
"""inv.py -- 把 memory 目录里所有"未闭/缺口/待办/尚未/未定"的散文原句抓成清单，
防止它们只活在文章里被忘掉。输出 OPEN_INVENTORY.md。"""
import os, io

M = r'C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory'
KW = ['未闭合', '未闭', '缺口', '待办', '尚未', '未定', '仍需']

head = [
    '# memory 里“旧未闭项”的原始清单（自动生成）',
    '',
    '> 用途：`tasks.json` 只覆盖已重新推导并建成断言的条目；',
    '> **本文件把 memory 散文中每一处 未闭/缺口/待办/尚未/未定 的原文抓出来**，',
    '> 防止它们只活在散文里被忘掉。每条带 `文件:行号`，可直接回查。',
    '> 转成正式任务时：在 `tasks.json` 增条目，并在此行标注 `[已转 Gx/Oxx]`。',
    '',
]

body = []
total = 0
files = 0
for fn in sorted(os.listdir(M)):
    if not fn.endswith('.md') or fn == 'MEMORY.md':
        continue
    p = os.path.join(M, fn)
    lines = io.open(p, encoding='utf-8').read().split('\n')
    hits = [(i + 1, l.strip()) for i, l in enumerate(lines)
            if any(k in l for k in KW)]
    if not hits:
        continue
    files += 1
    body.append('## %s  (%d 处)' % (fn, len(hits)))
    body.append('')
    for ln, txt in hits:
        total += 1
        if len(txt) > 220:
            txt = txt[:220] + '…'
        body.append('- `%s:%d` %s' % (fn, ln, txt))
    body.append('')

head.append('**合计 %d 处，涉及 %d 个 memory 文件**（生成时快照；重跑 `inv.py` 刷新）。'
            % (total, files))
head.append('')
head.append('---')
head.append('')

io.open('OPEN_INVENTORY.md', 'w', encoding='utf-8').write(
    '\n'.join(head + body) + '\n')
print('written: %d hits across %d files' % (total, files))
