"""在整个 mp_firingrange_zone.bin 里找最大的 cplane_t 连续表。

cplane_t 布局 (CoD4X / IW4): 3f normal + f dist + 1B type + 3B pad = 20 字节。
约束: |normal| ≈ 1, dist 有限, type 在小范围。
"""
import math
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)


def plane_ok(o):
    if o < 0 or o + 20 > N:
        return False
    n = struct.unpack_from('<3f', d, o)
    dist = struct.unpack_from('<f', d, o + 12)[0]
    if not all(math.isfinite(v) for v in n) or not math.isfinite(dist):
        return False
    l2 = n[0]*n[0] + n[1]*n[1] + n[2]*n[2]
    return abs(l2 - 1.0) < 0.005 and abs(dist) < 200000.0


print('scanning %s B ...' % format(N, ','))
runs = []
o = 0
while o < N - 20:
    if plane_ok(o):
        j = o
        cnt = 0
        while plane_ok(j):
            cnt += 1
            j += 20
        if cnt >= 30:
            runs.append((o, cnt))
        o = j
    else:
        o += 4

print('找到 %d 段 (>=30 连续平面)' % len(runs))
for off, cnt in sorted(runs, key=lambda x: -x[1])[:10]:
    print('  off=%-12d count=%-6d end=%d' % (off, cnt, off + cnt * 20))
