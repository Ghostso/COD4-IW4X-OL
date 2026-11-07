"""从 Bounds 表反推 brush 表。

Bounds = { float midPoint[3]; float halfSize[3]; } 24B
特征: midPoint 有限, halfSize 有限且非负, 且 halfSize 通常 > 0。

真实地图的 brush 数很大(与 18770 个 brushside 对应), 所以 Bounds 表应该是
一个很长的连续块。找出最长的 Bounds 连续段。
"""
import math
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)


def bounds_ok(o):
    if o < 0 or o + 24 > N:
        return False
    m = struct.unpack_from('<3f', d, o)
    h = struct.unpack_from('<3f', d, o + 12)
    for v in m:
        if not math.isfinite(v) or abs(v) > 50000:
            return False
    for v in h:
        if not math.isfinite(v) or v < 0 or v > 50000:
            return False
    # 至少一个 half > 0
    if not any(v > 1e-4 for v in h):
        return False
    return True


print('扫描 Bounds 连续段...')
runs = []
o = 0
while o < N - 24:
    if bounds_ok(o):
        j = o
        cnt = 0
        while bounds_ok(j):
            cnt += 1
            j += 24
        if cnt >= 50:
            runs.append((o, cnt))
        o = j
    else:
        o += 4

print('找到 %d 段 (>=50)' % len(runs))
for off, cnt in sorted(runs, key=lambda x: -x[1])[:15]:
    print('  off=%-12d count=%-6d end=%d' % (off, cnt, off + cnt * 24))
