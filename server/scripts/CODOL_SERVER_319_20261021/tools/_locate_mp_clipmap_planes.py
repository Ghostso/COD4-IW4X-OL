"""定位 mp_firingrange_zone.bin 的 planes / sides / brushes 结构。

coop 版里: planes 紧邻材质表之前, 材质表 4 项, side 指针的 delta 是常量。
对战版: 材质表 285 项在 42716679, side 表在 42720480。
这里按 side 指针反推 planes 表位置, 并核对 CoD4X 的 cplane_t (20B) 布局。
"""
import math
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)


def u16(o): return struct.unpack_from('<H', d, o)[0]
def u32(o): return struct.unpack_from('<I', d, o)[0]
def f32(o): return struct.unpack_from('<f', d, o)[0]


def plane_ok(o):
    if o < 0 or o + 20 > N:
        return False
    n = struct.unpack_from('<3f', d, o)
    dist = f32(o + 12)
    if not all(math.isfinite(x) for x in n) or not math.isfinite(dist):
        return False
    l2 = n[0]**2 + n[1]**2 + n[2]**2
    return abs(l2 - 1.0) < 0.02 and abs(dist) < 200000.0


SIDES_OFF = 42720480
print('zone size         = %s B' % format(N, ','))
print('brushside table   = %d' % SIDES_OFF)

# 收集 side 指针
ptrs = []
o = SIDES_OFF
while o + 8 <= N:
    p = u32(o)
    if not (0x30000000 <= p < 0x32000000):
        break
    ptrs.append(p)
    o += 8
print('brushside 数量    = %d' % len(ptrs))

if not ptrs:
    raise SystemExit('no side pointers')

# 反推 plane 表: ptr - PLANE_DELTA 应落在某个 20B 对齐的表里
# coop 版 delta = 0x30069e8d - 0x23f5a4
# 这里试: 假定 plane 表起点 P0, 则 (ptr - P0) % 20 == 0 且 plane_ok
print()
print('=== 通过指针反推 plane 表起点 ===')

# 先找所有可能的 plane 表 (连续 20B 合法平面)
runs = []
i = 0
while i < N - 20:
    if plane_ok(i):
        j = i
        cnt = 0
        while plane_ok(j):
            cnt += 1
            j += 20
        if cnt >= 8:
            runs.append((i, cnt))
        i = j
    else:
        i += 4

print('  找到 %d 段 >= 8 个连续合法平面' % len(runs))
for off, cnt in runs[:10]:
    print('    off=%d count=%d  (末项结束 %d)' % (off, cnt, off + cnt * 20))

# 用第一段长表验证指针
if runs:
    best = max(runs, key=lambda x: x[1])
    planes_off, plane_count = best
    print()
    print('  采用: planes_off=%d count=%d' % (planes_off, plane_count))
    delta = ptrs[0] - planes_off
    print('  ptrs[0]=0x%08X -> delta=0x%X (%d)' % (ptrs[0], delta, delta))
    bad = 0
    for k, p in enumerate(ptrs):
        rel = p - delta - planes_off
        if rel < 0 or rel % 20 or rel // 20 >= plane_count:
            bad += 1
    print('  指针解析失败数 = %d / %d' % (bad, len(ptrs)))
