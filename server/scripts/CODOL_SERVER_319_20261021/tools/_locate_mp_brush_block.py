"""通过 brushBounds (24B) + brushContents (4B) 反推 brush 总数与位置。

IW4X save() 顺序: ... brushes -> brushBounds -> brushContents -> smodelNodes
即 brush 表之后紧跟 bounds 表, 再跟 contents 表。

已知 side 表用到 18770 项, 索引最大 7577 平面。
先找 brush 数 N 使得:
  - brush 表 ptr 全部指向 side 表
  - 后面紧跟 N*24 的 bounds (全 finite, half>0)
  - 再后面 N*4 的 contents
"""
import math
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)

SIDES_OFF = 42720480
SIDE_COUNT = 18770
DELTA = 0x2FE4FC1E
SIDE_LO = DELTA + SIDES_OFF
SIDE_HI = SIDE_LO + SIDE_COUNT * 8
MAT_COUNT = 285


def u16(o): return struct.unpack_from('<H', d, o)[0]
def u32(o): return struct.unpack_from('<I', d, o)[0]


def brush_ok(o):
    if o < 0 or o + 36 > N:
        return False
    ns = u16(o)
    glass = u16(o + 2)
    sp = u32(o + 4)
    if ns > 64 or glass > 64:
        return False
    if sp:
        if not (SIDE_LO <= sp < SIDE_HI):
            return False
        if (sp - SIDE_LO) % 8:
            return False
        if (sp - SIDE_LO) // 8 + ns > SIDE_COUNT:
            return False
    for k in range(6):
        if u16(o + 12 + k * 2) >= MAT_COUNT:
            return False
    return True


def bounds_ok(o):
    if o < 0 or o + 24 > N:
        return False
    m = struct.unpack_from('<3f', d, o)
    h = struct.unpack_from('<3f', d, o + 12)
    for v in m:
        if not math.isfinite(v) or abs(v) > 100000:
            return False
    for v in h:
        if not math.isfinite(v) or v < 0 or v > 100000:
            return False
    return any(abs(v) > 1e-6 for v in h)


# 从每个 brush 候选段起点向后延伸, 看能否接上 bounds+contents
print('=== 延伸验证: brush 段 -> bounds 段 -> contents 段 ===')
results = []
o = 0
visited = set()
while o < N - 36:
    if brush_ok(o) and o not in visited:
        j = o
        cnt = 0
        while brush_ok(j):
            visited.add(j)
            cnt += 1
            j += 36
        if cnt >= 20:
            # j = brush 表结束, 检查 bounds
            nb = 0
            while bounds_ok(j + nb * 24):
                nb += 1
                if nb > cnt:
                    break
            # contents 全 4B 值, 只检查是否在合理范围
            if nb == cnt:
                results.append((o, cnt))
        o = j if cnt else o + 4
    else:
        o += 4

print()
print('=== brush+bounds 精确匹配 (%d 段) ===' % len(results))
for off, cnt in sorted(results, key=lambda x: -x[1])[:10]:
    print('  off=%-12d brush=%d bounds@end=%d' % (off, cnt, off + cnt * 36))
