"""找房间 UI 的动作定义来源。

已知: Active_To_Ready / Ready 等串在 EXE 代码段零引用 ⇒ UI 是数据驱动。

CODOOL 的 UI 有两种可能:
  A. GSC 脚本(编译进 .ff / fastfile)
  B. 引擎内置的 UI 系统(lua/menu 定义文件)

线索: 之前 memory 里记过 "本 build 的开发者接口清单" 提到
      UI 脚本内置函数表 0x00DAA400 (setdvar/exec/open...)。
      说明确实有 UI 脚本层。

先查: EXE 里有没有 lua / menu 相关的解释器串。
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
KEY = re.compile(rb'[A-Za-z0-9_./]{5,48}')
WANT = re.compile(rb'(?i)(lua|gsc|\.menu|\.txt|scriptmenu|menufile|ui/|ui_|script_)')

found = set()
for base, size, fn, prot in regions:
    if not (0x00C00000 <= base < 0x01000000):
        continue
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    d = CACHE[fn]
    if len(d) != size:
        continue
    for m in KEY.finditer(d):
        s = m.group(0)
        if WANT.search(s):
            found.add((base + m.start(), s.decode('latin1')))

print('候选串 %d 条（前 70）:' % len(found))
for va, s in sorted(found)[:70]:
    print('  0x%08X  %s' % (va, s))
