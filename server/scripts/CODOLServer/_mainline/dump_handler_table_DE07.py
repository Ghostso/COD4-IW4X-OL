"""读出 0xDE07xx 附近这张函数指针表, 判断索引语义。

已知: 0x7F1060 在 0xDE07BC, 0x7F10C0 在 0xDE07C0, 0x7F10E0 在 0xDE07E0。
说明是连续的表。往前找到表起点(一串指向 0x006Fxxxx~0x0080xxxx 的指针),
把整张表连同索引一起列出。
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


ANCHOR = 0x00DE07BC


def is_code_ptr(v):
    return 0x00400000 <= v < 0x01000000 and (v & 0x3) == 0


# 向前找表起点
start = ANCHOR
while True:
    prev = read_at(start - 4, 4)
    if not prev:
        break
    v = struct.unpack('<I', prev)[0]
    if is_code_ptr(v):
        start -= 4
    else:
        break

# 向后找表尾
end = ANCHOR
while True:
    nxt = read_at(end + 4, 4)
    if not nxt:
        break
    v = struct.unpack('<I', nxt)[0]
    if is_code_ptr(v):
        end += 4
    else:
        break

count = (end - start) // 4 + 1
print('表区间 0x%08X .. 0x%08X  共 %d 项' % (start, end, count))
print()
raw = read_at(start, count * 4)
for i in range(count):
    v = struct.unpack_from('<I', raw, i * 4)[0]
    mark = ''
    if start + i * 4 == 0x00DE07BC:
        mark = '   <- 0x7F1060 (房间推送入口)'
    elif start + i * 4 == 0x00DE07E0:
        mark = '   <- 0x7F10E0'
    print('  [%3d] 0x%08X = 0x%08X%s' % (i, start + i * 4, v, mark))
