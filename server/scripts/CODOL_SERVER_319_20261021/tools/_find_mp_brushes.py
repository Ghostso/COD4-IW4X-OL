"""精确定位 mp_firingrange 的 cbrush_t 表。

IW4X cbrush_t (36B):
  u16 numsides; u16 glassPieceIndex; cbrushside_t* sides; u8* baseAdjacentSide;
  u16 axialMaterialNum[2][3]; u8 firstAdjacentSideOffsets[2][3]; u8 edgeCount[2][3];

约束:
  - numsides <= 64
  - 若非 0, sides 指针必须精确解析到 side 表内的 8B 对齐位置
  - side 表共 18770 项, brush 的 sides 区间不能越界
  - axialMaterialNum 各值 < 285 (材质数)
"""
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


def brush_ok(o, need_side=True):
    """校验 o 处是否为一个合法 cbrush_t。"""
    if o < 0 or o + 36 > N:
        return False
    ns = u16(o)
    glass = u16(o + 2)
    sp = u32(o + 4)
    if ns > 64 or glass > 64:
        return False
    if sp != 0:
        if not (SIDE_LO <= sp < SIDE_HI):
            return False
        if (sp - SIDE_LO) % 8:
            return False
        idx = (sp - SIDE_LO) // 8
        if idx + ns > SIDE_COUNT:
            return False
        need_side = True
    else:
        need_side = False
    # axialMaterialNum[2][3] 在 +12
    for k in range(6):
        v = u16(o + 12 + k * 2)
        if v >= MAT_COUNT:
            return False
    return True


print('搜索 cbrush_t 连续表...')
runs = []
o = 0
while o < N - 36:
    if brush_ok(o):
        j = o
        cnt = 0
        while brush_ok(j):
            cnt += 1
            j += 36
        if cnt >= 10:
            runs.append((o, cnt))
            print('  run off=%-12d count=%d' % (o, cnt))
        o = j if cnt else o + 4
    else:
        o += 4

print()
print('共 %d 段' % len(runs))
if runs:
    best = max(runs, key=lambda x: x[1])
    print('最大: off=%d count=%d' % best)
