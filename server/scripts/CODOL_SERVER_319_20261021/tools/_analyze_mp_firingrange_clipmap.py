"""分析 mp_firingrange_zone.bin 的 clipmap 结构。

coop 版本用的是 4 项材质表(clip_player/clip_shot_block/clip_full/clip)，
对战版用的是 285 项表，布局不同。这里先定位各结构的位置。
"""
import math
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()


def u16(o): return struct.unpack_from('<H', d, o)[0]
def u32(o): return struct.unpack_from('<I', d, o)[0]
def f32(o): return struct.unpack_from('<f', d, o)[0]


def plane_ok(o):
    if o < 0 or o + 20 > len(d):
        return False
    n = struct.unpack_from('<3f', d, o)
    dist = f32(o + 12)
    if not all(math.isfinite(x) for x in n) or not math.isfinite(dist):
        return False
    l2 = n[0]**2 + n[1]**2 + n[2]**2
    return abs(l2 - 1.0) < 0.02 and abs(dist) < 200000.0


MAT_START = 42716679
MAT_END = 42720473

print('zone size = %s B' % format(len(d), ','))
print('material table: %d .. %d' % (MAT_START, MAT_END))
print()

# 材质表前面通常紧跟 cplane_t 数组 (每项 20 字节)
print('=== 材质表之前是否有连续的 cplane_t ===')
n = 0
o = MAT_START - 20
while plane_ok(o):
    n += 1
    o -= 20
print('  紧邻材质表前有 %d 个合法平面' % n)
if n:
    print('  平面区间: %d .. %d' % (o + 20, MAT_START))
    for i in range(min(6, n)):
        po = MAT_START - (n - i) * 20
        nm = struct.unpack_from('<3f', d, po)
        print('    plane[%2d] n=(%7.3f,%7.3f,%7.3f) dist=%9.2f type=%d'
              % (i, nm[0], nm[1], nm[2], f32(po + 12), d[po + 16]))

print()
print('=== 材质表之后 (brushside 表) ===')
# 材质表后通常跟 m7 pad 然后 brushside[]
for off in range(MAT_END, MAT_END + 32):
    if off % 4 == 0:
        v = u32(off)
        if 0x30000000 <= v < 0x32000000:
            print('  可能的指针表起点 off=%d 首指针=0x%08X' % (off, v))
            break
