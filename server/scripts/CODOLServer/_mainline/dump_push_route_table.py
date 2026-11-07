"""从内存转储里读出 (service, task) -> handler 注册表。

来源: 0x7E7C90 遍历 0xE376C08 起、stride 0x25D0、上界 0xE37B7A8 的表。
对每个表项 esi:
    [esi - 0x25B8]  标志字节1
    [esi - 0x25B7]  标志字节2
    [esi - 0x25A8]  service (与调用方 ebx 比较)
    [esi - 0x25A4]  task    (与调用方 edi 比较)
    [esi]           handler 函数指针
因此表项基址 entry = esi - 0x25B8, service = entry+0x10, task = entry+0x14,
handler = entry + 0x25B8。
"""
import os
import struct
import sys

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

regions = []
for line in open(os.path.join(D, 'regions.txt'), encoding='utf-8'):
    if line.startswith('#'):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4], int(p[2], 16)))
CACHE = {}


def blob(fn):
    if fn not in CACHE:
        CACHE[fn] = open(os.path.join(D, fn), 'rb').read()
    return CACHE[fn]


def read_at(va, n):
    for base, size, fn, _p in regions:
        if base <= va < base + size and va + n <= base + size:
            return blob(fn)[va - base:va - base + n]
    return None


START, END, STRIDE, DELTA = 0x0E376C08, 0x0E37B7A8, 0x25D0, 0x25B8

rows = []
esi = START
while esi < END:
    entry = esi - DELTA
    raw = read_at(entry, 0x20)
    if raw is None:
        rows.append((esi, None, None, None, None, None, 'unreadable'))
        esi += STRIDE
        continue
    f1 = raw[0]
    f2 = raw[1]
    svc, task = struct.unpack_from('<II', raw, 0x10)
    h = read_at(esi, 4)
    handler = struct.unpack('<I', h)[0] if h else None
    rows.append((esi, f1, f2, svc, task, handler, ''))
    esi += STRIDE

lines = ['# room channel (service, task) -> handler 注册表', '',
         '来源: MEMDUMP_20261027_v4, 表 0x%08X..0x%08X stride 0x%X' % (START, END, STRIDE),
         '', '| entry | flag1 | flag2 | service | task | handler |', '|---|---|---|---|---|---|']
for esi, f1, f2, svc, task, h, err in rows:
    if err:
        lines.append('| 0x%08X | %s |' % (esi, err))
        continue
    lines.append('| 0x%08X | %d | %d | %d | %d | 0x%08X |' % (esi, f1, f2, svc, task, h))

open(os.path.join(OUT, 'push_route_table.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
enabled = [r for r in rows if r[1] == 1 and r[2] == 1]
print('entries=%d  enabled=%d' % (len(rows), len(enabled)))
for r in enabled:
    print('  service=%d task=%d handler=0x%08X' % (r[3], r[4], r[5]))
