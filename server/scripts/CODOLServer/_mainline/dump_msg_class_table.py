"""读出房间消息类工厂表 0x82E1458（按 type 索引）。

0x634870 入口:
    readBits(3) -> 5 位头
    readData(8) -> type
    esi = [0x82E1458 + type*4]     <- 类/处理器指针
    if (esi == 0) 丢弃
    call esi

表项非零 = 该 type 被接受。全部读出来, 与我们的 ROOM_MSG_TYPE 对照。
"""
import os
import struct

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


TABLE = 0x082E1458
N = 0x60
raw = read_at(TABLE, N * 4)
if raw is None:
    raise SystemExit('table unreadable')

ours = {
    'startgame': 0x03, 'roominfo': 0x0F, 'ready': 0x10,
    'startcountingdown': 0x11, 'changeteam': 0x14, 'changeteamrequest': 0x15,
    'roomstateupdated': 0x17, 'vote': 0x1A, 'memberdetails': 0x1D,
    'memberdetailsquery': 0x1E, 'memberdetailsnoupdated': 0x1F,
    'joinmemberinfos': 0x25, 'inroomstatechange': 0x2D,
}
rev = {v: k for k, v in ours.items()}

print('type  handler      our-name')
print('----  -----------  --------')
nonzero = 0
for i in range(N):
    v = struct.unpack_from('<I', raw, i * 4)[0]
    if v:
        nonzero += 1
    name = rev.get(i, '')
    if v or name:
        print('0x%02X  0x%08X  %s' % (i, v, name))
print()
print('非零表项 = %d / %d' % (nonzero, N))
print()
print('我们推送用的 type 是否已注册:')
for k, t in ours.items():
    v = struct.unpack_from('<I', raw, t * 4)[0] if t < N else None
    print('  %-22s type=0x%02X  %s' % (k, t, ('已注册 0x%08X' % v) if v else '★ 未注册 → 丢弃'))
