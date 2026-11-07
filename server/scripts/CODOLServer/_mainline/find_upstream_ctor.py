"""定位客户端 11/4 上行的构造点。

思路: 上行 payload 里必有 service=11, task=4 的字段。任务帧格式(C# 参考):
    ... 明文 marker | service | task | ...
在内存转储里搜"写 service=11 + task=4"的代码特征，比较困难。

改用更可靠的办法: 既然 11/4 的 payload 结构已知(0a <u64> 13 08 <len> <batch> ...)，
搜代码里对 (11,4) 这一对做比较的立即数组合。

已确认的接收端符号:
  0x634870  房间消息分发(收)
  0x6371F0  房间信道(收)
要找的是**发送**侧: 构造 0a/13 08 这种 protobuf 风格字段的函数。

先做一个便宜的检查: 在转储里搜 0B 0x00 0x00 0x00 04 0x00 0x00 0x00 邻近出现。
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


print('=== 段表(.text 范围) ===')
for base, size, fn, prot in regions:
    if base in (0x00401000, 0x00400000) or prot & 0x20:
        print('  base=0x%08X size=0x%-8X prot=0x%X fn=%s' % (base, size, prot, fn))

print()
print('=== 搜 push 0xB / push 4 邻近 (0x6a 0x0b ... 0x6a 0x04) ===')
pat = b'\x6a\x0b'
hits = []
for base, size, fn, prot in regions:
    if not (prot & 0x20):
        continue
    data = blob(fn)
    if len(data) != size:
        continue
    i = data.find(pat)
    while i >= 0 and len(hits) < 400:
        seg = data[i:i + 40]
        if b'\x6a\x04' in seg:
            hits.append((base + i, seg.hex()))
        i = data.find(pat, i + 1)
print('  候选 %d 处' % len(hits))
for va, seg in hits[:20]:
    print('    0x%08X  %s' % (va, seg))
