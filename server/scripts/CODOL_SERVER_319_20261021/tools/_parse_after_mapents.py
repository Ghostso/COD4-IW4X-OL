"""从 mapents 之后的数据反推 clipmap 结构。

mapents 文本: 44,576,987 .. 44,761,773 (184,786 B)
之后 44,761,773 起是规律 8 字节记录:
    00 01 00 00 28 01 00 01
    00 01 00 00 28 01 00 02
    ...
看起来不是 u16 数组, 每项 8 字节, 含 0x0128 (=296)。

IW4X clipMap_t 里 leafbrushes 是 u16*。但这里像 8B 结构。
先验证步长和字段含义。
"""
import struct
from collections import Counter

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()

START = 44761773


def u16(o): return struct.unpack_from('<H', d, o)[0]
def u32(o): return struct.unpack_from('<I', d, o)[0]

print('=== 从 %d 起按 8 字节解析前 16 项 ===' % START)
for i in range(16):
    o = START + i * 8
    raw = d[o:o + 8]
    print('  [%2d] %s   u16=%s  u32=%s'
          % (i, raw.hex(' '),
             [u16(o + k * 2) for k in range(4)],
             [u32(o + k * 4) for k in range(2)]))

# 统计步长 8 的规律延续多久
print()
print('=== 按 8B 步长, 找规律结束位置 ===')
o = START
count = 0
while o + 8 <= len(d):
    w0 = u16(o)
    w1 = u16(o + 2)
    w2 = u16(o + 4)
    w3 = u16(o + 6)
    if not (w0 <= 2 and w1 <= 4 and w2 == 0x0128):
        break
    count += 1
    o += 8
print('  连续 %d 项, 结束于 %d' % (count, o))

print()
print('=== 结束位置之后 128 字节 ===')
for x in range(o, min(len(d), o + 128), 16):
    hx = ' '.join('%02X' % b for b in d[x:x + 16])
    asc = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in d[x:x + 16])
    print('%10d  %-48s %s' % (x, hx, asc))
