"""找房间按钮启用条件的代码。

思路: UI 按钮通常由一个"能否点"的标志控制。搜索
  1. 房间相关的 UI 元素名字符串(menu_ 前缀 / ready / vote / team)
  2. 引用这些字符串的代码
  3. 其中的条件判断

先做一次宽搜: 列出 .rdata 里所有含 room/ready/vote/team/map 的可打印串,
看有没有 UI 特有的命名风格。
"""
import os
import re

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))

CACHE = {}
KEY = re.compile(rb'[A-Za-z0-9_]{4,60}')
WANT = re.compile(rb'(?i)(room|ready|vote|team|changemap|mapvote|selectmap|startgame)')

seen = set()
found = []
for base, size, fn, prot in regions:
    if not (0x00C00000 <= base < 0x01000000):     # 只看 .rdata 一带
        continue
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    d = CACHE[fn]
    if len(d) != size:
        continue
    for m in KEY.finditer(d):
        s = m.group(0)
        if WANT.search(s) and s not in seen:
            seen.add(s)
            found.append((base + m.start(), s.decode('latin1')))

print('含关键词的可打印串 %d 条（显示前 80）:' % len(found))
for va, s in sorted(found)[:80]:
    print('  0x%08X  %s' % (va, s))
