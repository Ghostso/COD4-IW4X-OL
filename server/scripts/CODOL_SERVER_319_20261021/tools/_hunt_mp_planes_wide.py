"""在整个 mp_firingrange_zone.bin 中搜索 cplane_t 重复模式。

CoD4X cplane_t 20 字节: float normal[3], float dist, uint8 type, uint8 pad[3]

判据放宽: normal 的每个分量必须有限, |n|^2 在 [0.9, 1.1], dist 有限且在
[-100000, 100000]。找连续 >= 30 个这样的 20 字节记录。
"""
import math
import struct

P = r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'
d = open(P, 'rb').read()
N = len(d)


def ok(o):
    if o < 0 or o + 20 > N:
        return False
    n = struct.unpack_from('<3f', d, o)
    dist = struct.unpack_from('<f', d, o + 12)[0]
    for v in n:
        if not math.isfinite(v) or abs(v) > 1.5:
            return False
    if not math.isfinite(dist) or abs(dist) > 100000.0:
        return False
    l2 = n[0]*n[0] + n[1]*n[1] + n[2]*n[2]
    return 0.9 < l2 < 1.1


print('size %s' % format(N, ','))
runs = []
o = 0
while o < N - 20:
    if ok(o):
        j = o
        cnt = 0
        while ok(j):
            cnt += 1
            j += 20
        if cnt >= 30:
            runs.append((o, cnt))
            print('  run off=%-12d count=%d' % (o, cnt))
        o = j
    else:
        o += 4

print()
print('共 %d 段' % len(runs))
if runs:
    best = max(runs, key=lambda x: x[1])
    print('最大: off=%d count=%d' % best)
