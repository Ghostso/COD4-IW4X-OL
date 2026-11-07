"""确认房间推送走哪条 service 才能进 0x7F1060 -> 0x7E7C90 -> 0x634870。

0x7E7C90 是 (dword, dword) 路由表:
    esi 从 0xE376C08 起, stride 0x25D0, 上界 0xE37B7A8
    [esi-0x25B8] / [esi-0x25B7]  两个标志字节, 都必须 != 0
    [esi-0x25A8] == 第1个参数 (service)
    [esi-0x25A4] == 第2个参数 (task)
    [esi]        = handler 指针
早先读这张表全 0, 是因为读的时候房间还没建。这里改成:
扫描整块区域, 找出**任何**非零的 (flag, flag, dword, dword, handler) 组合。
"""
import os
import struct
import sys

D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem'
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


START, END, STRIDE = 0x0E376C08, 0x0E37B7A8, 0x25D0
DELTA = 0x25B8

print('扫描 0x%08X..0x%08X (stride 0x%X)' % (START, END, STRIDE))
found = []
esi = START
n = 0
while esi < END:
    n += 1
    entry = esi - DELTA
    raw = read_at(entry, 0x20)
    h = read_at(esi, 4)
    if raw and h:
        f1, f2 = raw[0], raw[1]
        svc, task = struct.unpack_from('<II', raw, 0x10)
        handler = struct.unpack('<I', h)[0]
        if (f1, f2) != (0, 0) or handler != 0:
            found.append((esi, f1, f2, svc, task, handler))
    esi += STRIDE

print('表项数=%d, 非空项=%d' % (n, len(found)))
for esi, f1, f2, svc, task, h in found:
    print('  esi=0x%08X flags=(%d,%d) service=%d task=%d handler=0x%08X'
          % (esi, f1, f2, svc, task, h))

if not found:
    print()
    print('全空 -> 该路由表在本次转储时刻尚未注册任何 (service,task)。')
    print('这说明房间推送的到达路径不是靠这张表建好后才成立的,')
    print('而更可能是: 客户端根本没把我们的推送当作房间消息(信封/信道不对)。')
