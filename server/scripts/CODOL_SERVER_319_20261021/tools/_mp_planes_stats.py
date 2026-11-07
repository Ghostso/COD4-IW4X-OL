"""用 brushside 的 firstAdjacentSideOffset / edgeCount 反推 brush 分组。

cbrushside_t 8B: { cplane_s* plane; u16 materialNum; i8 firstAdjacentSideOffset; i8 edgeCount; }

IW4X 的 brushside 是全局数组, cbrush_t 用 sides 指针 + numsides 描述自己那段。
如果 brush 表找不到, 可以退而求其次: 直接把全部 18770 个 side 当作
"独立的碰撞面" 使用 —— 每个 side 有平面, 平面 + 材质就足以做碰撞检测。

对服务端碰撞来说, brush 分组并非必需:
  - 平面碰撞测试只需要 (plane, contents)
  - CoD 的 trace 本质是逐平面裁剪 (clip to N planes)

所以: 先导出 (plane, material, contents) 三元组, 就能做基础碰撞。
"""
import struct
from collections import Counter

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()

PLANES_OFF = 5001523
PLANE_COUNT = 7587
SIDES_OFF = 42720480
SIDE_COUNT = 18770
DELTA = 0x2FE4FC1E

print('=== 平面统计 ===')
nz_up = nz_down = nz_side = 0
dist_hist = Counter()
for i in range(PLANE_COUNT):
    o = PLANES_OFF + i * 20
    nx, ny, nz = struct.unpack_from('<3f', d, o)
    dist = struct.unpack_from('<f', d, o + 12)[0]
    if nz > 0.5:
        nz_up += 1
    elif nz < -0.5:
        nz_down += 1
    else:
        nz_side += 1
print('  朝上 (z>0.5)   : %d  <- 地板' % nz_up)
print('  朝下 (z<-0.5)  : %d  <- 天花板' % nz_down)
print('  垂直 (|z|<=0.5): %d  <- 墙' % nz_side)

print()
print('=== 地板平面的高度分布 (dist 分布, 找主要地面) ===')
floors = []
for i in range(PLANE_COUNT):
    o = PLANES_OFF + i * 20
    nx, ny, nz = struct.unpack_from('<3f', d, o)
    dist = struct.unpack_from('<f', d, o + 12)[0]
    if nz > 0.5:
        floors.append((dist, nz, i))
floors.sort()
# 平面方程 n·x = dist, 对朝上的 z 平面: z = dist/nz
for dist, nz, idx in floors[:15]:
    print('  plane[%4d] nz=%.3f dist=%9.2f  -> z=%.2f' % (idx, nz, dist, dist/nz))
print('  ...')
for dist, nz, idx in floors[-8:]:
    print('  plane[%4d] nz=%.3f dist=%9.2f  -> z=%.2f' % (idx, nz, dist, dist/nz))

print()
print('=== side 材质分布 (前 10) ===')
mats = Counter()
for i in range(SIDE_COUNT):
    o = SIDES_OFF + i * 8
    mats[struct.unpack_from('<H', d, o + 4)[0]] += 1
for m, c in mats.most_common(10):
    print('  material %-4d : %d 次' % (m, c))
