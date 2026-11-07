"""验证 mp_firingrange 的 plane 表 (off=5001523, count=7587) 与 brushside 指针的对应关系,
并导出完整 clipmap。按 IW4X 结构:
  cplane_s      20B
  cbrushside_t   8B { cplane_s* plane; u16 materialNum; i8 fadj; i8 ecnt; }
  cbrush_t      36B
  Bounds        24B
"""
import math
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)

PLANES_OFF = 5001523
SIDES_OFF = 42720480


def plane_ok(o):
    if o < 0 or o + 20 > N:
        return False
    n = struct.unpack_from('<3f', d, o)
    dist = struct.unpack_from('<f', d, o + 12)[0]
    for v in n:
        if not math.isfinite(v) or abs(v) > 1.6:
            return False
    if not math.isfinite(dist) or abs(dist) > 200000.0:
        return False
    l2 = n[0]*n[0] + n[1]*n[1] + n[2]*n[2]
    return 0.85 < l2 < 1.15


# 精确测量 plane 表边界
start = PLANES_OFF
while plane_ok(start - 20):
    start -= 20
end = PLANES_OFF
while plane_ok(end):
    end += 20
count = (end - start) // 20
print('plane 表: %d .. %d  (%d 项)' % (start, end, count))

# 收集 side 指针
ptrs = []
o = SIDES_OFF
while o + 8 <= N:
    p = struct.unpack_from('<I', d, o)[0]
    if not (0x30000000 <= p < 0x32000000):
        break
    ptrs.append(p)
    o += 8
print('brushside: %d' % len(ptrs))

# 反推 delta: 最小指针应对应 index 0
uniq = sorted(set(ptrs))
base_vaddr = uniq[0]
delta = base_vaddr - start
print('base_vaddr=0x%08X  delta=0x%X' % (base_vaddr, delta))

bad = 0
maxidx = 0
for p in ptrs:
    rel = p - delta - start
    if rel < 0 or rel % 20:
        bad += 1
        continue
    idx = rel // 20
    if idx >= count:
        bad += 1
        continue
    if idx > maxidx:
        maxidx = idx
print('指针解析失败 %d / %d   最大索引 %d / %d' % (bad, len(ptrs), maxidx, count))

# 统计平面的 Z 分量(找地板)
nz_up = 0
nz_any = 0
for i in range(count):
    oo = start + i*20
    n = struct.unpack_from('<3f', d, oo)
    if abs(n[2]) > 0.5:
        nz_any += 1
        if n[2] > 0.5:
            nz_up += 1
print()
print('平面法线: |z|>0.5 的有 %d 项, 其中朝上(z>0.5) %d 项  <== 这些就是地板' % (nz_any, nz_up))
