"""找 Scaleform 侧的 room 相关绑定名。

Scaleform 里，C++ 通过 "invoke" 给 AS(Flash) 传值，名字是字符串。
搜 EXE 里所有可能与房间状态绑定的标识符。

重点找: 形如 xxxReady / roomXxx / IsXxx 的 CamelCase 标识符，
它们常是 Scaleform 的 ExternalInterface 方法名。
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
# Scaleform 方法名常见形态
PAT = re.compile(rb'\b(?:[A-Z][a-z]+){1,4}(?:Ready|Team|Room|Vote|Map|State)\b'
                 rb'|\b(?:Is|Get|Set|Can|Has)[A-Z][A-Za-z]{2,24}\b')

found = set()
for base, size, fn, prot in regions:
    if not (0x00C00000 <= base < 0x01000000):
        continue
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    d = CACHE[fn]
    if len(d) != size:
        continue
    for m in PAT.finditer(d):
        s = m.group(0).decode('latin1')
        if len(s) >= 8:
            found.add(s)

print('候选 Scaleform 风格标识符 %d 个' % len(found))
room = [s for s in found if re.search(r'Room|Ready|Team|Vote|Lobby', s)]
print('其中含 Room/Ready/Team/Vote/Lobby 的 %d 个:' % len(room))
for s in sorted(room):
    print('  %s' % s)
