"""放宽对齐约束找 brush 表: brush 段结束后, 允许 pad 到 128 对齐再出现 bounds。

IW4X: buffer->align(Utils::Stream::ALIGN_128) 用于 cbrush_t 和 brushBounds。
所以 brush 表起点和 bounds 表起点都应 128 对齐, 中间有 padding。
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
    return True


def bounds_run(o, n, limit=None):
    """从 o 开始连续 n 个 bounds 是否合法。"""
    if limit is None:
        limit = n
    cnt = 0
    while cnt < limit and bounds_ok(o + cnt * 24):
        cnt += 1
    return cnt


print('扫描 brush 段, 并对每个段尾尝试 128 对齐后的 bounds...')
o = 0
hits = []
while o < N - 36:
    if brush_ok(o):
        j = o
        cnt = 0
        while brush_ok(j):
            cnt += 1
            j += 36
        if cnt >= 15:
            # 段尾对齐到 128
            aligned = (j + 127) & ~127
            for pad in range(0, 129, 4):
                bo = j + pad
                bo_al = (bo + 127) & ~127
                got = bounds_run(bo_al, cnt)
                if got == cnt:
                    hits.append((o, cnt, bo_al))
                    break
        o = j if cnt else o + 4
    else:
        o += 4

print()
print('=== brush + (128对齐) bounds 全部匹配: %d 段 ===' % len(hits))
for off, cnt, bo in sorted(hits, key=lambda x: -x[1])[:12]:
    print('  brush_off=%-12d count=%-5d bounds_off=%-12d' % (off, cnt, bo))
